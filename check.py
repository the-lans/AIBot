import openai

from lib.config import Config


client = openai.OpenAI(api_key=Config.API_KEY_OPENAI, base_url=Config.OPENAI_URL)


if __name__ == "__main__":
    messages = [{"role": "system", "content": "Say this is a test"}]
    chat_completion = client.chat.completions.create(model="gpt-3.5-turbo-1106", messages=messages)
    ai_response_content = chat_completion.choices[0].message.content
    print(ai_response_content)
