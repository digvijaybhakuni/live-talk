from typing import final
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import whisper
import numpy as np

import uuid
import os

def load_distil_model():
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

# model_id = "distil-whisper/distil-large-v3"
    model_id = "distil-whisper/distil-small.en"


    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)

    processor = AutoProcessor.from_pretrained(model_id)

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        torch_dtype=torch_dtype,
        device=device,
    )
    return pipe

def load_whisper_model(model_id: str) -> whisper.Whisper:
    model_id = model_id or "small.en"
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    device = "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = whisper.load_model(model_id, device=device)
    return model

def transcibe_data(audio_bytes: bytes, audio_model: whisper.Whisper):
    # vector_bytes_str = str(audio_bytes)
    # vector_bytes_str_enc = vector_bytes_str.encode()
    # bytes_np_dec = vector_bytes_str_enc.decode('unicode-escape').encode('ISO-8859-1')[2:-1]
    # print(bytes_np_dec)
    # Convert in-ram buffer to something the model can use directly without needing a temp file.
    # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
    # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
    # audio_np = np.frombuffer(bytes_np_dec, dtype=np.int16).astype(np.float32) / 32768.0
    # audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    chunk_id = str(uuid.uuid1())
    chunk_file = f'temp/chunks/{chunk_id}.opus'
    try:
        with open(chunk_file, mode="wb") as chk:
            chk.write(audio_bytes)
        result = audio_model.transcribe(chunk_file, fp16=False)
        print('result >> \n', result)
        text = result['text'].strip()
        return text
    finally:
        pass
        # os.remove(chunk_file)


if __name__ == '__main__':
    import sys
    pipe = load_model()
    if pipe:
        file = sys.argv[1]
        result = pipe(file)

