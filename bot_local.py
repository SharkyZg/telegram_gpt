import asyncio
import os
from dotenv_vault import load_dotenv
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
        await update.message.reply_text("You are not authorized to use this bot.Your ID is: "+str(update.effective_user.id))
        return
    await update.message.reply_text("Hi! I'm your LangChain-powered bot. Ask me anything!")

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(os.getenv("AUTHORIZED_USER_ID")):
        await update.message.reply_text("You are not authorized to use this bot.Your ID is: "+str(update.effective_user.id))
        return

    user_input = update.message.text
    try:
        # If summary_chain.invoke is synchronous, run it in a thread
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, summary_chain.invoke, {"input": user_input})
        
        # Reply to the user
        await update.message.reply_text(response.content)
    except Exception as e:
        # Handle errors gracefully
        await update.message.reply_text(f"Error: {str(e)}")

# Main function
def main():
    # Replace with your Telegram bot token
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
