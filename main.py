import os
import json
from flask import Flask, request, jsonify
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from boto3 import Session
from langchain.schema import HumanMessage, AIMessage

# New Flask app initialization
app = Flask(__name__)


# LangChain setup
template = """
This is a conversation between a user and an AI assistant. The conversation history is as follows:

{history}

The user has just said: "{input}"

Please respond appropriately.
"""

summary_prompt = PromptTemplate.from_template(template)
summary_chain = summary_prompt | ChatOpenAI(model=os.getenv("GPT_MODEL"), temperature=os.getenv("MODEL_TEMPERATURE"))

# Add in-memory storage for user chat histories
user_memories = {}

# Updated memory manager
def get_memory(user_id):
    if user_id not in user_memories:
        # Initialize a new memory for the user if not already present
        user_memories[user_id] = ConversationBufferMemory(return_messages=True, output_key="output")
    return user_memories[user_id]

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
    if update.effective_user.id != int(authorized_user_id):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this bot. Your ID is: " + str(update.effective_user.id)
        )
        return
    await update.message.reply_text("Hi! I'm your LangChain-powered bot. Ask me anything!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
    if update.effective_user.id != int(authorized_user_id):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this bot. Your ID is: " + str(update.effective_user.id)
        )
        return

    user_id = update.effective_user.id
    user_input = update.message.text

    # Initialize LangChain memory for this user
    memory = get_memory(user_id)

    try:
        # Get conversation history
        raw_history = memory.chat_memory.messages  # LangChain message objects

        # Convert LangChain messages into ChatGPT-compatible format
        history = []
        for message in raw_history:
            if isinstance(message, HumanMessage):
                history.append({"role": "user", "content": message.content})
            elif isinstance(message, AIMessage):
                history.append({"role": "assistant", "content": message.content})

        # If summary_chain.invoke is synchronous, run it in an executor to avoid blocking
        response = summary_chain.invoke(
            {"input": user_input, "history": history}  # Pass the converted history here
        )

        print("Response:" + response.content)

        # Save user input and response to memory
        memory.save_context({"input": user_input}, {"output": response.content})
        # Send response to the user
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response.content
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Replace lambda_handler with Flask webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    async def process_update():
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        application = Application.builder().token(telegram_token).build()
        await application.initialize()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Get the bot instance
        bot = application.bot

        # Parse the Telegram update from the event body
        update_data = request.get_json(force=True)  # Extract JSON data from the request
        update = Update.de_json(update_data, bot)
        
        # Process the update
        await application.process_update(update)

        # Shutdown the application
        await application.shutdown()

    try:
        # Create and run an event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_update())
        loop.close()

        return jsonify({'message': 'Success'}), 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add Flask app runner
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 8080)))
