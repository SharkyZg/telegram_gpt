import os
import json
import asyncio
import boto3
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import DynamoDBChatMessageHistory
from boto3 import Session
from langchain.schema import HumanMessage, AIMessage

# Initialize a boto3 session
aws_session = Session(region_name=os.getenv("AWS_REGION"))

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name=os.getenv("AWS_REGION"))
invoice_chat_table = dynamodb.Table('InvoiceChat')

# LangChain setup
template = """
This is a conversation between a user and an AI assistant. The conversation history is as follows:

{history}

The user has just said: "{input}"

Please respond appropriately.
"""

summary_prompt = PromptTemplate.from_template(template)
summary_chain = summary_prompt | ChatOpenAI(model=os.getenv("GPT_MODEL"), temperature=os.getenv("MODEL_TEMPERATURE"))

# Create memory manager for chat history
def get_memory(user_id):
    table_name = "InvoiceChat"
    chat_history = DynamoDBChatMessageHistory(
        table_name=table_name,
        session_id=str(user_id),  # Use user_id as session identifier
        boto3_session=aws_session,  # Pass the boto3 session
        primary_key_name="UserID",  # Use the correct primary key
    )
    memory = ConversationBufferMemory(chat_memory=chat_history, return_messages=True, output_key="output")
    return memory

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
    if update.effective_user.id != int(authorized_user_id):
        await context.bot.send_message(
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
        response = await asyncio.get_running_loop().run_in_executor(
            None,
            summary_chain.invoke,
            {"input": user_input, "history": history}  # Pass the converted history here
        )

        # Save user input and response to memory
        memory.save_context({"input": user_input}, {"output": response.content})

        # Send response to the user
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response.content
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Lambda handler function
def lambda_handler(event, context):
    """
    The entry point for AWS Lambda to handle the Telegram updates.
    """
    try:
        # Define an async function to initialize and process the update
        async def process_update_async():
            # Create the application, set it up with the token
            telegram_token = os.getenv("TELEGRAM_TOKEN")
            application = Application.builder().token(telegram_token).build()
            await application.initialize()

            # Add handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            # Get the bot instance
            bot = application.bot

            # Parse the Telegram update from the event body
            update = Update.de_json(json.loads(event['body']), bot)
            
            # Process the update
            await application.process_update(update)

            # Shutdown the application
            await application.shutdown()

        # Run the async function
        asyncio.run(process_update_async())

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
