import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from huggingface_hub import hf_hub_download, login


class Command(BaseCommand):
    help = 'Download the model from HuggingFace'

    def add_arguments(self, parser):
        parser.add_argument('--dir', type=str, default='llama3/llama-3.2', help='Directory to download the model')
        parser.add_argument('--repo', type=str, default='hugging-quants/Llama-3.2-3B-Instruct-Q4_K_M-GGUF')
        parser.add_argument('--filename', type=str, default='llama-3.2-3b-instruct-q4_k_m.gguf', help='Model name')
        parser.add_argument('--force', action='store_true', help='Force download')

    def handle(self, *args, **options):
        token = os.getenv('HF_TOKEN')
        if not token:
            raise CommandError('You need to set the HF_TOKEN environment variable')
        login(token=token, add_to_git_credential=False)

        target_dir = Path(options['dir'])
        target_dir.mkdir(parents=True, exist_ok=True)

        downloaded_file = hf_hub_download(
            repo_id=options['repo'],
            filename=options['filename'],
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            force_download=options['force'],
            resume_download=True,
        )
        self.stdout.write(self.style.SUCCESS(f'Downloaded {downloaded_file}'))
