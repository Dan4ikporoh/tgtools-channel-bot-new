from __future__ import annotations

import random
from datetime import datetime
from typing import Any

import feedparser
import yaml
from bs4 import BeautifulSoup

from app.utils.text import normalize_text, safe_caption


BOOST_URL = "https://t.me/boost/tgbots_miniapps"


class ContentProvider:
    def __init__(self, sources_path: str, default_language: str = "ru") -> None:
        self.sources_path = sources_path
        self.default_language = default_language
        with open(sources_path, "r", encoding="utf-8") as f:
            self.sources = yaml.safe_load(f)

    def categories(self) -> list[str]:
        return list(self.sources["categories"].keys())

    async def fetch_item(self, category: str, seen_ids: set[str]) -> dict[str, Any] | None:
        entry = self.sources["categories"][category]
        source_type = entry["type"]

        if source_type == "rss":
            return await self._from_rss(category, entry, seen_ids)
        if source_type == "holiday":
            return await self._holiday_item(category)
        return None

    async def _from_rss(self, category: str, entry: dict[str, Any], seen_ids: set[str]) -> dict[str, Any] | None:
        urls = list(entry.get("feed_urls", []))
        random.shuffle(urls)

        for feed_url in urls:
            parsed = feedparser.parse(feed_url)
            candidates = parsed.entries[:20]
            random.shuffle(candidates)

            for item in candidates:
                external_id = item.get("id") or item.get("link")
                if not external_id or external_id in seen_ids:
                    continue

                title = normalize_text(item.get("title", "Интересная находка"))
                raw_summary = item.get("summary", item.get("description", ""))
                summary = safe_caption(raw_summary, limit=500)

                media_url = None
                media_candidates = item.get("media_content") or item.get("media_thumbnail") or []
                if media_candidates:
                    media_url = media_candidates[0].get("url")

                if not media_url:
                    soup = BeautifulSoup(raw_summary or "", "html.parser")
                    img = soup.find("img")
                    if img and img.get("src"):
                        media_url = img["src"]

                link = item.get("link")
                text = self._render_caption(category, title, summary)

                return {
                    "category": category,
                    "source_type": "rss",
                    "source_url": feed_url,
                    "external_id": external_id,
                    "title": title,
                    "text": text,
                    "media_url": media_url,
                    "link": link,
                    "boost_url": BOOST_URL,
                }

        return None

    async def _holiday_item(self, category: str) -> dict[str, Any] | None:
        today = datetime.utcnow().date()
        weekday_names = {
            0: "понедельник",
            1: "вторник",
            2: "среда",
            3: "четверг",
            4: "пятница",
            5: "суббота",
            6: "воскресенье",
        }
        weekday = weekday_names[today.weekday()]

        hooks = [
            "Мини-интерактив для своих 👇",
            "Немного актива в комментах 👇",
            "Тема дня для подписчиков 👇",
        ]
        questions = [
            "Что у вас сегодня по настроению: игры, дорога, дом или просто отдых?",
            "Что нового у вас сегодня: авто, тату, игры, работа или бытовые дела?",
            "Чем занимаетесь сегодня и что интересного можете посоветовать?",
        ]

        text = (
            f"📅 {random.choice(hooks)}\n\n"
            f"Сегодня {today.strftime('%d.%m.%Y')}, {weekday}.\n"
            f"{random.choice(questions)}\n\n"
            f"{random.choice(self._engagement_cta(category))}\n"
            f"{self._boost_line()}\n\n"
            f"{self._tag_for_category(category)}"
        )

        return {
            "category": category,
            "source_type": "holiday",
            "source_url": "local",
            "external_id": f"holiday:{today.isoformat()}",
            "title": f"День {today.strftime('%d.%m')}",
            "text": safe_caption(text, limit=1024),
            "media_url": None,
            "link": None,
            "boost_url": BOOST_URL,
        }

    def _render_caption(self, category: str, title: str, summary: str) -> str:
        summary = self._clean_summary(summary)
        intro = self._intro_for_category(category)
        question = self._question_for_category(category)
        emoji = self._emoji_for_category(category)
        tag = self._tag_for_category(category)
        cta = random.choice(self._engagement_cta(category))
        boost = self._boost_line()

        parts = [
            f"{emoji} {intro}",
            "",
            f"{title}",
        ]

        if summary:
            parts.extend(["", summary])

        if question:
            parts.extend(["", question])

        parts.extend(["", cta])
        parts.extend(["", boost])
        parts.extend(["", tag])

        return safe_caption("\n".join(parts), limit=1024)

    def _clean_summary(self, text: str) -> str:
        text = normalize_text(BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True))
        if not text:
            return ""
        if len(text) > 220:
            text = text[:220].rsplit(" ", 1)[0].rstrip(".,!?:;") + "…"
        return text

    def _boost_line(self) -> str:
        variants = [
            "⚡ Если у тебя Telegram Premium — отдай голос каналу по кнопке ниже.",
            "🚀 Поддержи канал голосом, если у тебя есть Telegram Premium.",
            "🔥 Есть Telegram Premium? Прожми голос за канал по кнопке ниже.",
        ]
        return random.choice(variants)

    def _intro_for_category(self, category: str) -> str:
        mapping = {
            "russia_news": random.choice([
                "Что нового по России",
                "Свежее из России",
                "Коротко о важном",
            ]),
            "auto": random.choice([
                "Что нового в авто теме",
                "Интересное про машины",
                "Полезное для водителей",
            ]),
            "games": random.choice([
                "Игровая тема дня",
                "Что интересного в играх",
                "Свежак для геймеров",
            ]),
            "tattoos": random.choice([
                "Тату тема дня",
                "Интересное из мира тату",
                "Идея для тату",
            ]),
            "lifehacks": random.choice([
                "Лайфхак дня",
                "Полезная штука на каждый день",
                "Заметка, которая может пригодиться",
            ]),
            "homemaking": random.choice([
                "Полезное для дома",
                "Бытовой совет дня",
                "Что пригодится дома и на кухне",
            ]),
            "garage_video": random.choice([
                "Видео для гаража",
                "Авто видео дня",
                "Что может пригодиться в гараже",
            ]),
            "home_video": random.choice([
                "Видео для дома",
                "Полезное видео по быту",
                "Короткое видео с пользой",
            ]),
            "funny_video": random.choice([
                "Смешное видео дня",
                "Немного угара",
                "Видео чисто поднять настроение",
            ]),
            "holidays": random.choice([
                "Интерактив для своих",
                "Тема дня",
                "Немного актива",
            ]),
        }
        return mapping.get(category, "Интересный пост")

    def _question_for_category(self, category: str) -> str:
        mapping = {
            "russia_news": random.choice([
                "Как вам такая новость?",
                "Что думаете по этому поводу?",
                "Норм тема или мимо?",
            ]),
            "auto": random.choice([
                "Что скажете по этой теме?",
                "У кого было что-то похожее?",
                "Полезно или спорно?",
            ]),
            "games": random.choice([
                "Во что сами сейчас играете?",
                "Играли бы в такое?",
                "Как вам тема?",
            ]),
            "tattoos": random.choice([
                "Сделали бы себе что-то в таком стиле?",
                "Как вам идея?",
                "Зашло или не ваше?",
            ]),
            "lifehacks": random.choice([
                "Берёте на заметку?",
                "Пробовали так делать?",
                "Полезно или и так знали?",
            ]),
            "homemaking": random.choice([
                "Пользуетесь такими советами?",
                "Пригодится дома?",
                "Норм лайфхак или мимо?",
            ]),
            "garage_video": random.choice([
                "Забрали бы такой совет себе в гараж?",
                "Полезная тема или мимо?",
                "Что скажете по этому видео?",
            ]),
            "home_video": random.choice([
                "Такой совет пригодится дома?",
                "Полезно или и так знали?",
                "Берёте себе на заметку?",
            ]),
            "funny_video": random.choice([
                "Ну как вам такое?",
                "Смешно или мимо?",
                "Оцените видос реакцией 😄",
            ]),
            "holidays": random.choice([
                "Пишите в комменты.",
                "Давайте пообщаемся.",
                "Что у вас сегодня интересного?",
            ]),
        }
        return mapping.get(category, "Что скажете?")

    def _emoji_for_category(self, category: str) -> str:
        mapping = {
            "russia_news": "📰",
            "auto": "🚗",
            "games": "🎮",
            "tattoos": "🖤",
            "lifehacks": "💡",
            "homemaking": "🏠",
            "garage_video": "🛠",
            "home_video": "📹",
            "funny_video": "😂",
            "holidays": "📅",
        }
        return mapping.get(category, "🔥")

    def _tag_for_category(self, category: str) -> str:
        mapping = {
            "russia_news": "#Россия #Новости",
            "auto": "#Авто #Машины",
            "games": "#Игры #Гейминг",
            "tattoos": "#Тату #Эскизы",
            "lifehacks": "#Лайфхак #Полезное",
            "homemaking": "#Дом #Быт",
            "garage_video": "#Гараж #АвтоВидео",
            "home_video": "#Дом #Видео",
            "funny_video": "#Смешное #Видео",
            "holidays": "#Интерактив #Общение",
        }
        return mapping.get(category, "#Пост")

    def _engagement_cta(self, category: str) -> list[str]:
        common = [
            "Поддержи пост реакцией 👍",
            "Пиши мнение в комментариях 👇",
            "Подписывайся, если любишь такой формат.",
            "Если хочешь больше такого контента — прожми реакцию.",
        ]

        category_map = {
            "russia_news": [
                "Если интересны новости по России — подписывайся.",
                "Мнение по теме кидай в комментарии 👇",
            ],
            "auto": [
                "Если нужна ещё авто тема — подписывайся.",
                "Свои советы и опыт пиши в комментариях 👇",
            ],
            "games": [
                "Если нужен ещё игровой контент — подписывайся.",
                "Во что играешь сейчас — напиши в комментариях 👇",
            ],
            "tattoos": [
                "Если зашло — кинь реакцию 🖤",
                "Подписывайся, если хочешь больше постов про тату.",
            ],
            "lifehacks": [
                "Полезно? Тогда поддержи пост реакцией 💡",
                "Свои лайфхаки можешь закинуть в комментарии 👇",
            ],
            "homemaking": [
                "Если пригодится — прожми реакцию 🏠",
                "Свои советы для дома кидай в комментарии 👇",
            ],
            "garage_video": [
                "Если тема гаража тебе близка — прожми реакцию 🛠",
                "Подписывайся, если нужен ещё гаражный и авто контент.",
            ],
            "home_video": [
                "Если полезно для дома — поддержи реакцией 📹",
                "Подписывайся, если нужен ещё бытовой контент.",
            ],
            "funny_video": [
                "Если улыбнуло — прожми реакцию 😂",
                "Скинь в комментарии, если хочешь ещё больше смешных постов.",
            ],
            "holidays": [
                "Реакцию для актива не жалеем 🔥",
                "Подписывайся, тут ещё будет много интересного.",
            ],
        }

        return category_map.get(category, []) + common
