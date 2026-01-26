# mappings.py

# 🎮 إعدادات الألعاب (تمت إضافة كافة الألعاب الجديدة)
GAMES_MAP = {
    "PUBG Mobile": ["ببجي", "PUBG"],
    "Free Fire": ["فري فاير", "FreeFire"],
    "Call of Duty": ["Call of Duty", "كول اوف ديوتي",],
    "Mobile Legends": ["Legends", "ليجند", "موبايل ليجند"],
    "Brawl Stars": ["Brawl", "براول", "ستارز"],
    "Clash of Clans": ["Clash of Clans", "كلاش اوف كلانس"],
    "Clash Royale": ["Clash Royale", "كلاش رويال"],
    "Yalla Ludo": ["Yalla", "يلا لودو", "يلا"],
    "Ludo Club": ["Ludo Club", "لودو كلوب"],
    "Jawaker": ["Jawaker", "جواكر"],
    "Roblox": ["Roblox", "روبلوكس"],
    "Minecraft": ["Minecraft","MINE CRAFT", "ماينكرافت"],
    "Fortnite": ["Fortnite", "فورت نايت"],
    "Valorant": ["Valorant", "فالورانت"],
    "League of Legends": ["League", "ليج", "لول", "Wild Rift"],
    "Delta Force": ["DeltaForce","Delta Force", "ديلتا"],
    "Dark legion": ["Dark legion", "Darklegion"],
    "Blood Strike": ["Blood", "بلود"],
    "8 Ball Pool": ["8BALL POOL", "بلياردو"],
    "eFootball PES": ["PES", "بيس", "football"],
    "FC Mobile (FIFA)": ["FC","FCMobile", "فيفا", "FIFA"],
    "TopTop": ["TopTop", "توب توب"],
    "Hay Day": ["Hay Day", "هاي داي"],
    "King of avalon": ["Kingofavalon", "King of avalon"],
    "ARENA BREAKOUT": ["ARENA BREAKOUT", "ARENABREAKOUT"],
    "LordsMobile ": ["LordsMobile","Lords Mobile", "لوردز موبايل","لوردس مويايل"],
    "Honor of king ": ["Honor of king","Honorofking", "هونور اوف كينج",],
    "النجاة من الصقيع": ["النجاة من الصقيع",],
    "حرب الممالك": ["حرب الممالك",],
    "دمج الممالك": ["دمج الممالك",],
    "Genshin Impact": ["Genshin", "قنشن"]
}

# 📱 إعدادات التطبيقات والخدمات
APPS_MAP = {
    "💳 بطاقات إلكترونية": [ "Visa", "Steam", "PlayStation", "Nintendo", "Razer", "iTunes", "Xbox", "Google"],

    "💵 أرصدة وعملات": ["شام كاش", "usdt", "MTN", "سيريتل",],

    "📱 سوشيال ميديا": [
        "التطبيقات", "انستجرام", "فيسبوك", "تيك توك", "تويتر", "يوتيوب",
        "Bigo", "Sango", "Yalla", "Likee", "Kwai", "Telegram Premium"
    ],

    "🌐 شركات إنترنت": ["نت", "ليزر", "امواج", "برونت", "ليما", "اينت", "تكامل", "دنيا", "ناس", "ناسا", "طيو"],

    "✈️ خدمات تليجرام": ["تليجرام", "Telegram"],

    "🎬 اشتراكات تطبيقات": [
        "اشتراكات", "شاهد", "NetFlix", "We Tv", "OSN", "Spotify", "انغامي",
        "Apple", "Zain 4K", "IP TV", "Watch", "نوفا", "فيو", "Blue", "LOOK",
        "TOD", "Disney", "Canva"
    ],

    "🔒 اشتراكات VPN": ["VPN", "1.1.1.1", "Proxy"],
    "👤 حسابات جاهزة": ["حسابات", "ChatGPT", "Gmail"]
}

# 💎 إعدادات الوايت (الوساطة)
WHITE_MAP = {
    "شراء USDT": "contact_admin",
    "شراء شام كاش ($)": "contact_admin",
    "شراء شام كاش (SYP)": "contact_admin"
}

# ⚠️ هام جداً لعمل البوت (دمج القوائم للبحث)
ALL_MAPS = {**GAMES_MAP, **APPS_MAP}