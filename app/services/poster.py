from __future__ import annotations

import io
import logging
import textwrap

import httpx
from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

BOOST_URL = "https://t.me/boost/tgbots_miniapps"
COMMENTS_URL = "https://t.me/tgtoolschat"


def build_post_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 ГОЛОС", url=BOOST_URL),
                InlineKeyboardButton(text="💬 КОММЕНТЫ", url=COMMENTS_URL),
            ]
        ]
    )


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]

    for path in font_candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue

    return ImageFont.load_default()


def _wrap_text(text: str, width: int) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    return textwrap.wrap(text, width=width)


def generate_cover_image(item: dict) -> bytes:
    width, height = 1280, 720

    title = (item.get("title") or "Интересный пост").strip()
    category = (item.get("category") or "контент").replace("_", " ").upper()

    bg_variants = [
        ((20, 24, 44), (59, 89, 152)),
        ((18, 18, 18), (64, 64, 64)),
        ((27, 33, 58), (101, 78, 163)),
        ((21, 48, 74), (39, 95, 174)),
        ((46, 21, 54), (133, 37, 121)),
        ((22, 64, 56), (46, 125, 50)),
    ]
    c1, c2 = bg_variants[abs(hash(title)) % len(bg_variants)]

    img = Image.new("RGB", (width, height), c1)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / max(height - 1, 1)
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # затемнение снизу для читаемости
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle([(0, height * 0.45), (width, height)], fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(52, bold=True)
    meta_font = _load_font(28, bold=False)
    small_font = _load_font(24, bold=False)

    # метка категории
    category_text = f"TG TOOLS • {category}"
    draw.rounded_rectangle((60, 50, 420, 105), radius=22, fill=(255, 255, 255))
    draw.text((82, 68), category_text[:28], font=small_font, fill=(20, 20, 20))

    # заголовок
    title_lines = _wrap_text(title, 28)[:5]
    y = 220
    for line in title_lines:
        draw.text((70, y), line, font=title_font, fill=(255, 255, 255))
        y += 72

    footer_lines = [
        "Подпишись • поставь реакцию • напиши комментарий • проголосуй за канал",
        "@tgbots_miniapps",
    ]
    draw.text((70, 610), footer_lines[0], font=meta_font, fill=(240, 240, 240))
    draw.text((70, 650), footer_lines[1], font=meta_font, fill=(255, 255, 255))

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=92)
    return output.getvalue()


class Poster:
    def __init__(self, bot: Bot, channel_id: str) -> None:
        self.bot = bot
        self.channel_id = channel_id

    async def publish(self, item: dict) -> int:
        reply_markup = build_post_keyboard()
        media_url = item.get("media_url")

        if media_url:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.get(media_url)
                    resp.raise_for_status()

                clean_url = media_url.split("?")[0].lower()
                ext = clean_url.split(".")[-1] if "." in clean_url else ""

                image_exts = {"jpg", "jpeg", "png", "webp"}
                video_exts = {"mp4", "mov", "m4v", "webm"}

                if ext in image_exts:
                    photo = BufferedInputFile(resp.content, filename=f"post.{ext}")
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=item["text"],
                        reply_markup=reply_markup,
                    )
                    return msg.message_id

                if ext in video_exts:
                    video = BufferedInputFile(resp.content, filename=f"post.{ext}")
                    msg = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=item["text"],
                        reply_markup=reply_markup,
                        supports_streaming=True,
                    )
                    return msg.message_id

                content_type = resp.headers.get("content-type", "").lower()

                if content_type.startswith("image/"):
                    guessed_ext = content_type.split("/")[-1].split(";")[0] or "jpg"
                    photo = BufferedInputFile(resp.content, filename=f"post.{guessed_ext}")
                    msg = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=photo,
                        caption=item["text"],
                        reply_markup=reply_markup,
                    )
                    return msg.message_id

                if content_type.startswith("video/"):
                    guessed_ext = content_type.split("/")[-1].split(";")[0] or "mp4"
                    video = BufferedInputFile(resp.content, filename=f"post.{guessed_ext}")
                    msg = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=video,
                        caption=item["text"],
                        reply_markup=reply_markup,
                        supports_streaming=True,
                    )
                    return msg.message_id

            except Exception as exc:
                logger.warning("Could not send media %s: %s", media_url, exc)

        # если картинки нет — генерируем обложку по заголовку поста
        try:
            generated = generate_cover_image(item)
            photo = BufferedInputFile(generated, filename="generated_cover.jpg")
            msg = await self.bot.send_photo(
                chat_id=self.channel_id,
                photo=photo,
                caption=item["text"],
                reply_markup=reply_markup,
            )
            return msg.message_id
        except Exception as exc:
            logger.warning("Could not generate cover image: %s", exc)

        msg = await self.bot.send_message(
            chat_id=self.channel_id,
            text=item["text"],
            disable_web_page_preview=False,
            reply_markup=reply_markup,
        )
        return msg.message_id
