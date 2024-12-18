from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultCachedVideo


inline_query_router = Router()

@inline_query_router.inline_query()
async def inline_query(query: InlineQuery):
    video_note_id = query.query
    try:
        result = InlineQueryResultCachedVideo(
            id="1",
            video_file_id=video_note_id,
            title="Видео поздравление",
        )
        await query.answer([result], cache_time=0)
    except:
        await query.answer([], cache_time=0)