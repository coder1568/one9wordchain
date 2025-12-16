import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import aiofiles
import aiofiles.os
import matplotlib.pyplot as plt
from aiocache import cached
from aiogram import types
from aiogram.utils.markdown import quote_html
from asyncpg import Record
from matplotlib.dates import DateFormatter
from matplotlib.ticker import MaxNLocator

from .. import dp, db
from ..utils import has_star, send_groups_only_message


@dp.message_handler(commands=["stat", "stats", "stalk"])
async def cmd_stats(message: types.Message) -> None:
    rmsg = message.reply_to_message
    user = (rmsg.forward_from or rmsg.from_user) if rmsg else message.from_user
    res = await db.fetchrow("SELECT * FROM player WHERE user_id = ?;", user.id)

    if not res:
        await message.reply(
            f"No statistics for {user.get_mention(as_html=True)}!",
            allow_sending_without_reply=True,
        )
        return

    # Get rank
    rank = await db.fetchval(
        """
        SELECT COUNT(*) FROM player
        WHERE (total_score, user_id) >= (?, ?)
        """,
        res["total_score"],
        res["user_id"],
    )
    total_players = await db.fetchval("SELECT COUNT(*) FROM player;")
    mention = user.get_mention(
        name=user.full_name + (" \u2b50\ufe0f" if await has_star(user.id) else ""), as_html=True
    )
    text = (
        f"\U0001f4ca Statistics for {mention}:\n"
        f"<b>{res['game_count']}</b> games played\n"
        f"<b>{res['win_count']} ({res['win_count'] / res['game_count']:.0%})</b> games won\n"
        f"<b>{res['word_count']}</b> total words played\n"
        f"<b>{res['letter_count']}</b> total letters played"
    )
    if res["longest_word"]:
        text += f"\nLongest word: <b>{res['longest_word'].capitalize()}</b>"
    await message.reply(text, parse_mode=types.ParseMode.HTML, allow_sending_without_reply=True)


@dp.message_handler(commands="groupstats")
@send_groups_only_message
async def cmd_groupstats(message: types.Message) -> None:
    # TODO: Add top players in group (max 5) to message
    row = await db.fetchrow(
        """
        SELECT 
            COUNT(DISTINCT user_id) as player_cnt, 
            COUNT(DISTINCT game_id) as game_cnt, 
            SUM(word_count) as word_cnt, 
            SUM(letter_count) as letter_cnt
        FROM gameplayer
        WHERE group_id = ?;
        """,
        message.chat.id
    )
    
    if not row:
        await message.reply("No statistics available for this group yet.")
        return
        
    player_cnt = row['player_cnt'] or 0
    game_cnt = row['game_cnt'] or 0
    word_cnt = row['word_cnt'] or 0
    letter_cnt = row['letter_cnt'] or 0
    await message.reply(
        (
            f"\U0001f4ca Statistics for <b>{quote_html(message.chat.title)}</b>\n"
            f"<b>{player_cnt}</b> players\n"
            f"<b>{game_cnt}</b> games played\n"
            f"<b>{word_cnt}</b> total words played\n"
            f"<b>{letter_cnt}</b> total letters played"
        ),
        parse_mode=types.ParseMode.HTML,
        allow_sending_without_reply=True
    )


@cached(ttl=5)
async def get_global_stats() -> str:
    # Get group and game counts
    group_game_row = await db.fetchrow(
        "SELECT COUNT(DISTINCT group_id) as group_cnt, COUNT(*) as game_cnt FROM game;"
    )
    group_cnt = group_game_row['group_cnt'] if group_game_row else 0
    game_cnt = group_game_row['game_cnt'] if group_game_row else 0
    
    # Get player, word, and letter counts
    player_stats = await db.fetchrow(
        """
        SELECT 
            COUNT(*) as player_cnt, 
            COALESCE(SUM(word_count), 0) as word_cnt, 
            COALESCE(SUM(letter_count), 0) as letter_cnt 
        FROM player;
        """
    )
    
    player_cnt = player_stats['player_cnt'] if player_stats else 0
    word_cnt = player_stats['word_cnt'] if player_stats else 0
    letter_cnt = player_stats['letter_cnt'] if player_stats else 0

    return (
        "\U0001f4ca Global statistics\n"
        f"*{group_cnt}* groups\n"
        f"*{player_cnt}* players\n"
        f"*{game_cnt}* games played\n"
        f"*{word_cnt}* total words played\n"
        f"*{letter_cnt}* total letters played"
    )


@dp.message_handler(commands="globalstats")
async def cmd_globalstats(message: types.Message) -> None:
    await message.reply(await get_global_stats(), allow_sending_without_reply=True)


@dp.message_handler(is_owner=True, commands=["trend", "trends"])
async def cmd_trends(message: types.Message) -> None:
    try:
        days = int(message.get_args() or 14)
        assert days > 1, "smh"
    except (ValueError, AssertionError) as e:
        await message.reply(f"`{e.__class__.__name__}: {str(e)}`", allow_sending_without_reply=True)
        return

    t = time.time()  # Measure time used to generate graphs
    today = datetime.now().date()

    async def get_daily_games() -> Dict[str, Any]:
        rows = await db.fetch(
            """
            SELECT date(start_time) as d, COUNT(*) as count
            FROM game
            WHERE date(start_time) >= ?
            GROUP BY d
            ORDER BY d;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )
        return {row['d']: row['count'] for row in rows}

    async def get_active_players() -> Dict[str, Any]:
        rows = await db.fetch(
            """
            SELECT date(game.start_time) as d, COUNT(DISTINCT gameplayer.user_id) as count
            FROM gameplayer
            INNER JOIN game ON gameplayer.game_id = game.id
            WHERE date(game.start_time) >= ?
            GROUP BY d
            ORDER BY d;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )
        return {row['d']: row['count'] for row in rows}

    async def get_active_groups() -> Dict[str, Any]:
        rows = await db.fetch(
            """
            SELECT date(start_time) as d, COUNT(DISTINCT group_id) as count
            FROM game
            WHERE date(start_time) >= ?
            GROUP BY d
            ORDER BY d;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )
        return {row['d']: row['count'] for row in rows}

    async def get_cumulative_groups() -> Dict[str, Any]:
        rows = await db.fetch(
            """
            SELECT d, total
            FROM (
                SELECT d, SUM(count) OVER (ORDER BY d) as total
                FROM (
                    SELECT d, COUNT(group_id) as count
                    FROM (
                        SELECT DISTINCT group_id, date(MIN(start_time)) as d
                        FROM game
                        GROUP BY group_id
                    ) s1
                    GROUP BY d
                ) s2
            ) s3
            WHERE d >= ?
            ORDER BY d;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )
        return {row['d']: row['total'] for row in rows}

    async def get_cumulative_players() -> Dict[str, Any]:
        rows = await db.fetch(
            """
            SELECT d, total
            FROM (
                SELECT d, SUM(count) OVER (ORDER BY d) as total
                FROM (
                    SELECT d, COUNT(user_id) as count
                    FROM (
                        SELECT DISTINCT user_id, date(MIN(game.start_time)) as d
                        FROM gameplayer
                        INNER JOIN game ON gameplayer.game_id = game.id
                        GROUP BY user_id
                    ) ud
                    GROUP BY d
                ) du
            ) ds
            WHERE d >= ?
            ORDER BY d;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )
        return {row['d']: row['total'] for row in rows}

    async def get_game_mode_play_cnt() -> List[Dict[str, Any]]:
        return await db.fetch(
            """
            SELECT COUNT(game_mode) as count, game_mode
            FROM game
            WHERE date(start_time) >= ?
            GROUP BY game_mode
            ORDER BY count;
            """,
            (today - timedelta(days=days - 1)).isoformat()
        )

    # Execute multiple db queries at once for speed
    (
        daily_games,
        active_players,
        active_groups,
        cumulative_groups,
        cumulative_players,
        game_mode_play_cnt
    ) = await asyncio.gather(
        get_daily_games(),
        get_active_players(),
        get_active_groups(),
        get_cumulative_groups(),
        get_cumulative_players(),
        get_game_mode_play_cnt()
    )

    # Handle the possible issue of no games played in a day,
    # so there are no gaps in the cumulative graphs
    # (probably never happens)

    dt = today - timedelta(days=days)
    for i in range(days):
        dt += timedelta(days=1)
        if dt not in cumulative_groups:
            if i == 0:
                async with pool.acquire() as conn:
                    cumulative_groups[dt] = await conn.fetchval(
                        "SELECT COUNT(DISTINCT group_id) FROM game WHERE start_time::DATE <= $1;", dt
                    )
            else:
                cumulative_groups[dt] = cumulative_groups[dt - timedelta(days=1)]

    dt = today - timedelta(days=days)
    for i in range(days):
        dt += timedelta(days=1)
        if dt not in cumulative_players:
            if i == 0:
                async with pool.acquire() as conn:
                    cumulative_players[dt] = await conn.fetchval(
                        """\
                        SELECT COUNT(DISTINCT user_id)
                            FROM gameplayer
                            INNER JOIN game ON game_id = game.id
                            WHERE start_time <= $1;""",
                        dt
                    )
            else:
                cumulative_players[dt] = cumulative_players[dt - timedelta(days=1)]

    while os.path.exists("trends.jpg"):  # Another /trend command has not finished processing
        await asyncio.sleep(0.1)

    # Draw graphs

    plt.figure(figsize=(15, 8))
    plt.subplots_adjust(hspace=0.4)
    plt.suptitle(f"Trends in the Past {days} Days", size=25)

    tp = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    f = DateFormatter("%b %d" if days < 180 else "%b" if days < 335 else "%b %Y")

    sp = plt.subplot(231)
    sp.xaxis.set_major_formatter(f)
    sp.yaxis.set_major_locator(MaxNLocator(integer=True))  # Force y-axis intervals to be integral
    plt.setp(sp.xaxis.get_majorticklabels(), rotation=45, horizontalalignment="right")
    plt.title("Games Played", size=18)
    plt.plot(tp, [daily_games.get(i, 0) for i in tp])
    plt.ylim(ymin=0)

    sp = plt.subplot(232)
    sp.xaxis.set_major_formatter(f)
    sp.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.setp(sp.xaxis.get_majorticklabels(), rotation=45, horizontalalignment="right")
    plt.title("Active Groups", size=18)
    plt.plot(tp, [active_groups.get(i, 0) for i in tp])
    plt.ylim(ymin=0)

    sp = plt.subplot(233)
    sp.xaxis.set_major_formatter(f)
    sp.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.setp(sp.xaxis.get_majorticklabels(), rotation=45, horizontalalignment="right")
    plt.title("Active Players", size=18)
    plt.plot(tp, [active_players.get(i, 0) for i in tp])
    plt.ylim(ymin=0)

    plt.subplot(234)
    labels = [i[1] for i in game_mode_play_cnt]
    colors = [
        "dark maroon",
        "dark peach",
        "orange",
        "leather",
        "mustard",
        "teal",
        "french blue",
        "booger",
        "pink"
    ]
    total_games = sum(i[0] for i in game_mode_play_cnt)
    slices, text = plt.pie(
        [i[0] for i in game_mode_play_cnt],
        labels=[
            f"{i[0] / total_games:.1%} ({i[0]})" if i[0] / total_games >= 0.03 else ""
            for i in game_mode_play_cnt
        ],
        colors=["xkcd:" + c for c in colors[len(colors) - len(game_mode_play_cnt):]],
        startangle=90
    )
    plt.legend(slices, labels, title="Game Modes Played", fontsize="x-small", loc="best")
    plt.axis("equal")

    sp = plt.subplot(235)
    sp.xaxis.set_major_formatter(f)
    sp.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.setp(sp.xaxis.get_majorticklabels(), rotation=45, horizontalalignment="right")
    plt.title("Cumulative Groups", size=18)
    plt.plot(tp, [cumulative_groups[i] for i in tp])

    sp = plt.subplot(236)
    sp.xaxis.set_major_formatter(f)
    sp.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.setp(sp.xaxis.get_majorticklabels(), rotation=45, horizontalalignment="right")
    plt.title("Cumulative Players", size=18)
    plt.plot(tp, [cumulative_players[i] for i in tp])

    # Save the plot as a jpg and send it
    plt.savefig("trends.jpg", bbox_inches="tight")
    plt.close("all")
    async with aiofiles.open("trends.jpg", "rb") as f:
        await message.reply_photo(f, caption=f"Generation time: `{time.time() - t:.3f}s`")
    await aiofiles.os.remove("trends.jpg")
