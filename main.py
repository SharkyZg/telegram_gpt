import os
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, ContextTypes
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()

# LangChain setup
template = """
    {input}
    """
summary_prompt = PromptTemplate.from_template(template)
summary_chain = summary_prompt | ChatOpenAI(model="gpt-4o", temperature=0)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("AUTHORIZED_USER_ID")):
        await update.message.reply_text("You are not authorized to use this bot. Your ID is: "+str(update.effective_user.id))
        return
    await update.message.reply_text("Hi! I'm your LangChain-powered bot. Ask me anything!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("AUTHORIZED_USER_ID")):
        await update.message.reply_text("You are not authorized to use this bot. Your ID is: "+str(update.effective_user.id))
        return

    user_input = update.message.text
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, summary_chain.invoke, {"input": user_input})
        await update.message.reply_text(response.content)
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

# Lambda handler function
def lambda_handler(event, context):
    """
    The entry point for AWS Lambda to handle the Telegram updates.
    """
    print("event: ", event)
    try:
        # Parse the Telegram update from the event body
        update = Update.de_json(json.loads(event['body']), None)
        
        # Create the application, set it up with the token
        application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Manually call the handler for the update
        application.process_update(update)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

