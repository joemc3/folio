"""GitHub language colors — subset of commonly used languages."""

LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "Lua": "#000080",
    "Perl": "#0298c3",
    "R": "#198CE7",
    "Dart": "#00B4AB",
    "Elixir": "#6e4a7e",
    "Clojure": "#db5855",
    "Haskell": "#5e5086",
    "OCaml": "#3be133",
    "Zig": "#ec915c",
    "Nim": "#ffc200",
    "Julia": "#a270ba",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "SCSS": "#c6538c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Objective-C": "#438eff",
    "PowerShell": "#012456",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "Nix": "#7e7eff",
    "HCL": "#844FBA",
    "Terraform": "#5c4ee5",
}

DEFAULT_COLOR = "#8b8b8b"


def get_language_color(language: str) -> str:
    return LANGUAGE_COLORS.get(language, DEFAULT_COLOR)


def get_accent_from_languages(languages: dict[str, float]) -> str:
    if not languages:
        return DEFAULT_COLOR
    top_lang = max(languages, key=languages.get)
    return get_language_color(top_lang)
