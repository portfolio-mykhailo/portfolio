from pathlib import Path

language_flags = {
    'en': '🇬🇧English',
    'ru': '🇷🇺Русский',
    'pl': '🇵🇱Polski',
    'ua': '🇺🇦Українська',
    'de': '🇩🇪Deutsch',
    'fr': '🇫🇷Français',
    'it': '🇮🇹Italiano',
    'es': '🇪🇸Español',
    'pt': '🇵🇹Português',
    'hi': '🇮🇳हिन्दी',
    'cn': '🇨🇳中文',
    'ja': '🇯🇵日本語',
    'ko': '🇰🇷한국어',
    'ar': '🇸🇦العربية',
}


async def list_files_async(directory: str) -> list:
    file_names = []
    for file in Path(directory).glob('*.ini'):
        if file.is_file():
            file_name = file.stem
            file_names.append(file_name)
    return file_names


async def prettify_language_codes(lang_list: list) -> tuple:
    key_list = [code for code, flag in language_flags.items() if code in lang_list]
    value_list = [flag for code, flag in language_flags.items() if code in lang_list]

    return value_list, key_list


async def reverse_prettify_language_codes(language):
    for key, value in language_flags.items():
        if value == language:
            return key
    return None
