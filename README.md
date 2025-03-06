# Discord Message Retrieval Bot

The purpose of this bot is to satiate something that I had in mind for the general users of our Discord - curating a bot that has the ability to interact, respond and answer various questions that can also pull from the wealth of information that already exists in the Discord.

The best way to accomplish this task without having to constantly worry about Discord's rate limits (or even the availability of their servers, for the most part), is to aggregate all of the messages that have been sent through the main channel and then stuff that in a remote database that our bot can Discord as part of its RAG pipeline/operations. Then, from there, we can use `langchain` or some other SDK to facilitate the whole pipeline. But we'll cross that bridge when we get to it.

> *As an added bonus, I'm also going to be exporting all of the messages that I have sent on Telegram as well* (which dates back to 2017), *and adding that to the total RAG resources that our bot can pull from. Additionally, this bot will be capable of going online to perform research as well. There are already several different agetns out there that are capable of performing the DeepResearch task that we've seen Gemini and OpenAI tout in recent days and weeks. I don't want to sidetrack people too much, so for this repo, we're just going to focus on the whole message retrieval thing with Discord. Keep in mind that this has to occur in a server where you have administrator privileges.*

