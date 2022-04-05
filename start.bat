@echo off
set /p CHANNEL="Channel: "

echo Starting Twitch Bot with channel: %CHANNEL%
python twitchbot.py %CHANNEL%