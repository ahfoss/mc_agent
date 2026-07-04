class CommandRegistry:
    """
    Registry for managing and dispatching bot chat commands.
    """
    def __init__(self):
        # List of tuples: (trigger_phrase, handler_function)
        self.commands = []

    def register(self, trigger_phrase, handler_func):
        """
        Registers a function to trigger when a phrase is spoken in chat.
        """
        self.commands.append((trigger_phrase.lower(), handler_func))

    def dispatch(self, bot, username, message):
        """
        Checks chat messages and fires matching handlers.
        Returns True if a command was matched and executed, False otherwise.
        """
        message_lower = message.lower()
        for trigger, handler in self.commands:
            if trigger in message_lower:
                bot.log(f"Command matched: '{trigger}' (from {username})")
                try:
                    handler(bot, username, message)
                except Exception as e:
                    bot.log(f"Error executing command '{trigger}': {e}")
                    bot.bot.chat(f"I encountered an error executing '{trigger}'.")
                return True
        bot.log(f"No command matched for message: '{message}'")
        return False
