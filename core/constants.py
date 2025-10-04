
from .paths import ROOTDIR

# Optional extra sheet on export: environment variable can override
DETAILS_XLSX_DEFAULT = str(ROOTDIR / "extra_details.xlsx")

MONSTERS = [
    "None","Rathian","Fatalis","Kelbi","Mosswine","Bullfango","Yian_Kut_Ku","Lao_Shan_Lung","Cephadrome","Felyne_1",
    "Veggie_Elder","Rathalos","Aptonoth","Genprey","Diablos","Khezu","Velociprey","Gravios","Felyne_2","Vespoid",
    "Gypceros","Plesioth","Basarios","Melynx","Hornetaur","Apceros","Monoblos","Velocidrome","Gendrome","Rocks_0",
    "Ioprey","Iodrome","Pugis","Kirin","Cephalos","Giaprey","Crimson_Fatalis","Pink_Rathian","Blue_Yian_Kut_Ku",
    "Purple_Gypceros","Yian_Garuga","Silver_Rathalos","Gold_Rathian","Black_Diablos","White_Monoblos","Red_Khezu",
    "Green_Plesioth","Black_Gravios","Daimyo_Hermitaur","Azure_Rathalos","Ashen_Lao_Shan_Lung","Blangonga","Congalala",
    "Rajang","Kushala_Daora","Shen_Gaoren","Great_Thunderbug","Shakalaka","Yama_Tsukami_1","Chameleos",
    "Rusted_Kushala_Daora","Blango","Conga","Remobra","Lunastra","Teostra","Hermitaur","Shogun_Ceanataur","Bulldrome",
    "Anteka","Popo","White_Fatalis","Yama_Tsukami_2","Ceanataur","Hypnocatrice","Lavasioth","Tigrex","Akantor",
    "Bright_Hypnoc","Lavasioth_Subspecies","Espinas","Orange_Espinas","White_Hypnoc","Akura_Vashimu","Akura_Jebia",
    "Berukyurosu","Cactus_01","Gorge_Objects","Gorge_Rocks","Pariapuria","White_Espinas","Kamu_Orugaron","Nono_Orugaron",
    "Raviente","Dyuragaua","Doragyurosu","Gurenzeburu","Burukku","Erupe","Rukodiora","Unknown","Gogomoa","Kokomoa",
    "Taikun_Zamuza","Abiorugu","Kuarusepusu","Odibatorasu","Disufiroa","Rebidiora","Anorupatisu","Hyujikiki","Midogaron",
    "Giaorugu","Mi_Ru","Farunokku","Pokaradon","Shantien","Pokara","Dummy","Goruganosu","Aruganosu","Baruragaru",
    "Zerureusu","Gougarf","Uruki","Forokururu","Meraginasu","Diorekkusu","Garuba_Daora","Inagami","Varusaburosu",
    "Poborubarumu","Duremudira","UNK_0","Felyne","Blue_NPC","UNK_1","Cactus_Varusa","Veggie_Elders","Gureadomosu",
    "Harudomerugu","Toridcless","Gasurabazura","Kusubami","Yama_Kurai","Dure_2nd_District","Zinogre","Deviljho",
    "Brachydios","Berserk_Laviente","Toa_Tesukatora","Barioth","Uragaan","Stygian_Zinogre","Guanzorumu","Starving_Deviljho",
    "UNK","Egyurasu","Voljang","Nargacuga","Keoaruboru","Zenaserisu","Gore_Magala","Blinking_Nargacuga","Shagaru_Magala",
    "Amatsu","Elzelion","Musou_Dure","Rocks_1","Seregios","Bogabadorumu","Unknown_Blue_Barrel","Musou_Bogabadorumu",
    "Costumed_Uruki","Musou_Zerureusu","PSO2_Rappy","King_Shakalaka"
]

NOTES_TEXT = (
    "Musou Variants\n"
    "--------------\n"
    "• Musou Guanzorumu — 0F / 15\n"
    "• Musou Mi Ru — 0F / 15\n"
    "• Musou Duremudira — 0F / 15\n"
    "• Musou Eruzerion — 0B / 11\n"
    "• Musou Bogabadorumu — 0B / 11\n"
    "• Musou Zerureusu — 0B / 11\n"
    "• Starving Deviljho — 0B / 11\n"
    "• Howling Zinogre — 0B / 11\n\n"

    "Shiten Variants\n"
    "---------------\n"
    "• Shiten Unknown — 0D / 13\n"
    "• Shiten Disufiroa — 0D / 13\n\n"

    "Other Variants\n"
    "--------------\n"
    "• Red Aura Monsters (Shogun, Tigrex, Espinas, Black Gravios, Khezu, Lavasioth) — 0C / 12\n"
    "• Phantom Dora — 8 / 08\n"
    "• Phantom Rajang — 8 / 08\n\n"

    "Special Variants\n"
    "----------------\n"
    "• Starving Deviljho (Fire Version) — 0C / 12\n"
    "• Fishman Plesioth (Event) — 0C / 12\n"
    "• Developer Gogomoa — 6 / 06\n"
    "• Kut-Ku with Glasses — 6 / 06\n\n"

    "Groups\n"
    "------\n"
    "• Zeniths — 16\n"
    "• Supremacy Monsters (Unknown, Odi, Pariapuria, Doragyurosu,  — 9\n"
)

