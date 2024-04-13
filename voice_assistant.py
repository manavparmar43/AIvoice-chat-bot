import pyaudio
import wave, os, uuid

from openai import OpenAI
from pathlib import Path

from playsound import playsound
import speech_recognition as sr
import tiktoken
from database import store_chat_history

client = OpenAI(
    api_key="openai-key",
)


msg_data = [{"role": "system", "content": "You are a helpful assistant."}]
file_list = []
max_token = 100
available_token = 100


# generate token for messages limit
def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = (
            4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        )
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print(
            "Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613."
        )
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print(
            "Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613."
        )
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


# This Funcation is working convert audio to text
def convert_audio_to_text(file_user_path, uuid_code):
    audio_file = open(file_user_path, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1", file=audio_file, response_format="text"
    )

    create_msg_payload(transcript, uuid_code)


# this funcation create message create msg payload and send to ai funcation
def create_msg_payload(transcript, uuid_code):
    msg_data.append({"role": "user", "content": f"{transcript}"})
    res = send_msg_request_to_chatgpt_turbo(msg_data)
    # store_chat_history(
    #     {"role": "user", "content": f"{transcript}"},
    #     {"role": "assistant", "content": f"{res}"},
    # )
    msg_data.append({"role": "assistant", "content": f"{res}"})
    speech_file_path = Path(__file__).parent / f"mp3/assistant_{uuid_code}.mp3"
    file_list.append(f"mp3/assistant_{uuid_code}.mp3")
    convert_text_to_audio(res, speech_file_path)
    playsound(str(speech_file_path))
    manage_token()


# manage token
def manage_token():
    global available_token
    token = num_tokens_from_messages(msg_data) # 50 
    print(f"token:{token}")
    if token < max_token: # 50 < 100
        available_token = max_token - token  # 100 - 50 = 50 (available_token)
    else: 
        count_token = 0 
        i = 1 
        while i < len(msg_data): 
            message_tokens = num_tokens_from_messages([msg_data[i]]) # 10 , 20
            print(f"message_token:{message_tokens}")
            count_token += message_tokens # first time : 10 ,  30
            msg_data.pop(i)
            total_token = num_tokens_from_messages(msg_data) # 
            print(f"total_token: {total_token}")
            if total_token == max_token:
                i += 1   
            if total_token < max_token:
                available_token = count_token
            else:
                i += 1        
    print(f"After: {available_token}")


# record voice
def record_voice():
    uuid_code = str(uuid.uuid1())[:8]
    file_path = f"mp3/user_{uuid_code}.mp3"
    duration = 5
    sample_rate = 44100
    chunk_size = 10243
    audio_format = pyaudio.paInt16
    channels = 2
    p = pyaudio.PyAudio()
    print("\nyou are record the voice only 4 seconds...\n")
    print("Recording Starting......\n")
    stream = p.open(
        format=audio_format,
        channels=channels,
        rate=sample_rate,
        input=True,
        frames_per_buffer=chunk_size,
    )

    print("Recording...\n")

    frames = []
    for i in range(0, int(sample_rate / chunk_size * duration)):
        data = stream.read(chunk_size)
        frames.append(data)

    print("Recording complete.....\n")
    file_list.append(file_path)
    stream.stop_stream()
    stream.close()
    p.terminate()

    with wave.open(file_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(audio_format))
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    convert_audio_to_text(file_path, uuid_code)


# convert text to audio
def convert_text_to_audio(msg, speech_file_path):
    response = client.audio.speech.create(model="tts-1", voice="shimmer", input=msg)
    response.stream_to_file(speech_file_path)


# send_msg_request_to_chatgpt_turbo
def send_msg_request_to_chatgpt_turbo(msg):
    global msg_data
    msg_data.append({"role": "user", "content": f"{msg}"})
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=msg_data, max_tokens=available_token
    )
    msg_data.append({"role": "assistant", "content": f"{response.choices[0].message.content}"})
    print(f"ai: {response.choices[0].message.content}")
    manage_token()
    print("before", available_token)
    return 


# remove mp3 file list
def remove_file(file_lists):
    for i in file_lists:
        os.remove(i)


if __name__ == "__main__":
    while True:
        # record_voice()
        user_msg=input("You: ")
        if user_msg.lower()== "e":
            break
        send_msg_request_to_chatgpt_turbo(user_msg)

        
