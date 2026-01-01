#!/usr/bin/env python3
"""
Probe which SSML features are accepted by Amazon Polly for a given voice/engine.

Usage:
    python test_polly_ssml.py --voice Matthew --engine neural --region us-east-1
"""
import argparse
from typing import List, Dict

import boto3
from botocore.exceptions import ClientError
from app.config import settings


TEST_CASES: List[Dict[str, str]] = [
    {
        "name": "plain",
        "ssml": "<speak>This is a plain sentence for Polly testing.</speak>",
    },
    {
        "name": "prosody_rate",
        "ssml": "<speak><prosody rate='90%'>Slightly slower speech.</prosody></speak>",
    },
    {
        "name": "prosody_pitch_plus",
        "ssml": "<speak><prosody pitch='+5%'>Slightly higher pitch.</prosody></speak>",
    },
    {
        "name": "prosody_pitch_minus",
        "ssml": "<speak><prosody pitch='-5%'>Slightly lower pitch.</prosody></speak>",
    },
    {
        "name": "prosody_volume",
        "ssml": "<speak><prosody volume='+2dB'>Slightly louder.</prosody></speak>",
    },
    {
        "name": "emphasis",
        "ssml": "<speak>This is <emphasis level='moderate'>important</emphasis>.</speak>",
    },
    {
        "name": "breaks",
        "ssml": "<speak>Wait<break time='300ms'/>for it.</speak>",
    },
    {
        "name": "say_as_digits",
        "ssml": "<speak><say-as interpret-as='digits'>1234</say-as></speak>",
    },
    {
        "name": "amazon_domain_news",
        "ssml": "<speak><amazon:domain name='news'>Breaking news test.</amazon:domain></speak>",
    },
    {
        "name": "amazon_domain_conversational",
        "ssml": "<speak><amazon:domain name='conversational'>Conversational test.</amazon:domain></speak>",
    },
    {
        "name": "amazon_effect_drc",
        "ssml": "<speak><amazon:effect name='drc'>Dynamic range compression test.</amazon:effect></speak>",
    },
    {
        "name": "amazon_effect_whispered",
        "ssml": "<speak><amazon:effect name='whispered'>Whispered test.</amazon:effect></speak>",
    },
]


def run_probe(voice: str, engine: str, region: str, access_key: str, secret_key: str) -> None:
    if access_key and secret_key:
        client = boto3.client(
            "polly",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
    else:
        client = boto3.client("polly", region_name=region)

    print(f"🔎 Polly SSML probe | voice={voice} engine={engine} region={region}")
    print("=" * 72)
    for case in TEST_CASES:
        name = case["name"]
        ssml = case["ssml"]
        try:
            client.synthesize_speech(
                Text=ssml,
                TextType="ssml",
                OutputFormat="mp3",
                VoiceId=voice,
                Engine=engine,
            )
            print(f"✅ {name}")
        except ClientError as exc:
            print(f"❌ {name}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default="Matthew")
    parser.add_argument("--engine", default="neural")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--access-key", default=None)
    parser.add_argument("--secret-key", default=None)
    args = parser.parse_args()

    access_key = args.access_key or settings.aws_access_key_id or None
    secret_key = args.secret_key or settings.aws_secret_access_key or None
    region = args.region or settings.aws_region or "us-east-1"

    run_probe(
        voice=args.voice,
        engine=args.engine,
        region=region,
        access_key=access_key,
        secret_key=secret_key,
    )


if __name__ == "__main__":
    main()
