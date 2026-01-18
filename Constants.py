from Modules.Dataclasses import *

ORIGINAL_FRAME_SIZE = (1920, 1080)
BOT_FRAME_SIZE = (1100, 570)
MAIN_FRAME_SIZE = (1280, 720)
SPAWN_POSITION = (300, 200)

# state checks are where the checked states are stored.
# checked states are states that contain information to colors and pixels for a wanted state
# the porgram willl uses these to check if the pixels specified are withing 7 unit so color to the specified color
# I.E. if the color is 56, 56, 56. then 59, 50, 54 will pass, and 67, 12, 255 will fail

GENERIC_STATES = {
    "pairing_screen": {
        "color": (209, 209, 209),
        "positions": [(64, 485), (1213, 485)],
        "tol": 10,
    },
    "home_screen": {
        "color": (45, 45, 45),
        "positions": [(41, 562), (1233, 626), (665, 164)],
        "tol": 10,
    },
    "controller_screen": {
        "color": (69, 69, 69),
        "positions": [(142, 303), (722, 206), (694, 502)],
        "tol": 10,
    },
    "controller_connected": {
        "color": (254, 254, 254),
        "positions": [(73, 694), (108, 693)],
        "tol": 10,
    },
    "player_1": {
        "color": (12, 252, 155),
        "positions": [(148, 484), (152, 484)],
        "tol": 10,
    },
    "black_screen": {
        "color": (0, 0, 0),
        "positions": [(263, 401), (1076, 258), (93, 677)],
        "tol": 10,
    },
    "white_screen": {
        "color": (255, 255, 255),
        "positions": [(263, 401), (1076, 258), (93, 677)],
        "tol": 10,
    },
    "change_user": {
        "color": (243, 200, 42),
        "positions": [(163, 484), (173, 484)],
        "tol": 10,
    },
    "local_communication": {
        "color": (28, 25, 15),
        "positions": [(159, 590), (217, 159)],
        "tol": 10,
    },
    "playing": {
        "path": "Media/HOME_Images/Playing.png",
        "roi": (194, 400, 136, 35)
    },
}

SWSH_STATES = {
    # screens
    "title_screen": {
        "color": (255, 255, 254),
        "positions": [(717, 78), (557, 79)],
        "tol": 10,
    },
    "box_screen": {
        "color": (249, 254, 233),
        "positions": [(802, 87), (868, 665)],
        "tol": 10,
    },
    "battle_screen": {
        "color": (255, 255, 254),
        "positions": [
            (287, 694),
            (322, 619),
            (971, 30),
            (949, 81)
        ]
    },
    "menu_screen": {
        "color": (66, 32, 206),
        "positions": [
            (574, 3),
            (1043, 3),
            (160, 657)
            ],
    },
    # in game
    "in_game": {
        "color": (254, 254, 254),
        "positions": [(54, 690), (8, 690)],
        "tol": 10,
    },
    "pokemon_in_box": {
        "color": (217, 218, 219),
        "positions": [(979, 158), (972, 345), (904, 386)],
        "tol": 10,
    },
    "egg_in_box": {
        "color": (251, 255, 242),
        "positions": [(979, 158), (972, 345), (904, 386)],
        "tol": 10,
    },
    "shiny_symbol": {
        "color": (102, 102, 102),
        "positions": [(1253, 122), (1263, 113)],
        "tol": 10,
    },
    "encounter_text": {
        "color": (51, 51, 51),
        "positions": [(854, 663), (366, 655), (1138, 670)],
        "tol": 10,
    },
    "text_box": {
        "color": (38, 38, 38),
        "positions": [
            (67, 579),
            (1259, 631),
            (1245, 691)
        ]
    },
    "dark_text_box": {
        "color": (51, 51, 51),
        "positions": [
            (337, 674),
            (384, 578),
            (842, 673),
            (896, 581)
        ]
    },
    "menu": { 
        "pokedex": {
            "index": 0,
            "color": (1, 0, 1),
            "rois": [(130, 107, 75, 113)],
            "positions": [
                (130, 107),
                (130, 220),
                (205, 107),
                (205, 220)
            ]
        },
        "pokemon": {    
            "index": 1,
            "color": (1, 0, 1),
            "rois": [(366, 107, 75, 113)],
            "positions": [
                (366, 107),
                (366, 220),
                (441, 107),
                (441, 220)
            ]
        },
        "bag": {    
            "index": 2,
            "color": (1, 0, 1),
            "rois": [(602, 107, 75, 113)],
            "positions": [
                (602, 107),
                (602, 220),
                (679, 107),
                (679, 220)
            ]
        },
        "league_card": {
            "index": 3,
            "color": (1, 0, 1),
            "rois": [(838, 107, 75, 113)],
            "positions": [
                (838, 107),
                (838, 220),
                (917, 107),
                (917, 220)
            ]
        },
        "save": {
            "index": 4,
            "color": (1, 0, 1),
            "rois": [(1074, 107, 75, 113)],
            "positions": [
                (1074, 107),
                (1074, 220),
                (1155, 107),
                (1155, 220)
            ]
        },
        "town_map": {
            "index": 5,
            "color": (1, 0, 1),
            "rois": [(130, 347, 75, 113)],
            "positions": [
                (130, 347),
                (130, 460),
                (205, 347),
                (205, 460)
            ]
        },
        "pokemon_camp": {
            "index": 6,
            "color": (1, 0, 1),
            "rois": [(366, 347, 75, 113)],
            "positions": [
                (366, 347),
                (366, 460),
                (441, 347),
                (441, 460)
            ]
        },
        "mystery_gift": {
            "index": 7,
            "color": (1, 0, 1),
            "rois": [(602, 347, 75, 113)],
            "positions": [
                (602, 347),
                (602, 460),
                (679, 347),
                (679, 460)
            ]
        },
        "vs": {
            "index": 8,
            "color": (1, 0, 1),
            "rois": [(838, 347, 75, 113)],
            "positions": [
                (838, 347),
                (838, 460),
                (917, 347),
                (917, 460)
            ]
        },
        "options": {
            "index": 9,
            "color": (1, 0, 1),
            "rois": [(1074, 347, 75, 113)],
            "positions": [
                (1074, 347),
                (1074, 460),
                (1155, 347),
                (1155, 460)
            ]
        }
    },
    "bag": {
        # Medicine, Poké Balls, Battle Items, Berries, Other Items, TMs, Treasures, Ingredients, Key Items
        "pouch_names": (799, 106, 257, 33), #Bag Name
        "items": [
        (799, 106, 257, 33), #Bag Name
        (683, 149, 344, 46), #item 1
        (683, 206, 344, 46), #item 2
        (683, 263, 344, 46), #item 3
        (683, 320, 344, 46), #item 4
        (683, 377, 344, 46), #item 5
        (683, 434, 344, 46), #item 6
        (683, 491, 344, 46), #item 7
        ]
    },
    # rois
    "pokemon_name": (313, 395, 143, 31),
    "encounter_name": (93, 578, 900, 101)
}

BDSP_STATES = {
    # screens
    "loading_title": {
        "color": (224, 225, 225),
        "positions": [(509, 432), (830, 443)],
        "tol": 10,
    },
    "title_screen": {
        "color": (17, 210, 245),
        "positions": [(364, 205), (542, 225)],
        "tol": 10,
    },
    "box_screen": {
        "color": (238, 230, 158),
        "positions": [(837, 84), (358, 87)],
        "tol": 10,
    },
    # in game
    "multi_select": {
        "color": (80, 164, 76),
        "positions": [(258, 8), (257, 59)],
        "tol": 10,
    },
    "pokemon_in_box": {
        "color": (182, 162, 100),
        "positions": [(983, 166), (997, 195)],
        "tol": 10,
    },
    "egg_in_box": {
        "color": (234, 234, 234),
        "positions": [(986, 166), (995, 166)],
        "tol": 10,
    },
    "shiny_symbol": {
        "color": (70, 53, 230),
        "positions": [(1258, 115), (1248, 125)],
        "tol": 10,
    },
    "text_box": {
        "color": (250, 251, 251),
        "positions": [(781, 595), (273, 611), (1019, 593), (1021, 695)],
        "tol": 10,
    },
    "hatchery_pokecenter": {
        "color": (255, 255, 254),
        "positions": [(1108, 580), (1251, 600), (1253, 638)],
        "tol": 10,
    },
    "daycare_sign": {
        "path": "Media/BDSP_Images/Day_Care_Sign.png",
        "roi": (240, 160, 180, 180)
    },
    "egg_acquired": {
        "color": (101, 234, 243),
        "positions": [(943, 141), (941, 253), (339, 270), (338, 142)],
        "tol": 10,
    },
    "egg_hatching": {
        "path": "Media/BDSP_Images/Hatched.png",
    },
    "poketch": {
        "color": (48, 0, 144),
        "positions": [(1257, 190), (1257, 129)],
        "tol": 10,
    },
    #   rois
    "nursery_man": (165, 343, 40, 54),
    "text_box_roi": {
        "roi": (268, 591, 757, 107)
        },
    # program specific
}

LA_STATES = {}

SV_STATES = {
    # screens
    "title_screen": {
        "color": (13, 220, 243),
        "positions": [
            (870, 238),
            (970, 216),
            (824, 206),
            (1029, 236)
            ],
    },
    "menu_screen": {
        "color": (252, 252, 252),
        "positions": [
            (626, 683),
            (989, 687),
            (1187, 686),
            (1197, 697)
            ],
    },
    "box_screen": {
        "color": (251, 251, 251),
        "positions": [
            (329, 621),
            (329, 605),
            (321, 613),
            (338, 613)
        ]
    },
    "all_box_screen": {
        "color": (255, 255, 254),
        "positions": [
            (979, 619),
            (709, 618),
            (702, 613)
        ]
    },
    # in game
    "pokemon_in_box": {
        "color": (13, 212, 244),
        "positions": [
            (854, 404),
            (904, 438),
            (1275, 1),
            (1267, 46)
            ],
    },
    "egg_in_box": {
        "color": (1, 0 ,1),
        "positions": [
            (904, 21),
            (904, 29),
            (922, 40),
            (926, 40)
        ]
    },
    "pokemon_highlighted": {
        # box offsets are: left is from 300 to 384, down is from 133 to 217
        "color": (33, 215, 218),
        "roi": (300, 133, 82, 81),
        "positions": [
            (376, 138),
            (376, 136),
            (304, 138),
            (304, 136)
        ]
    },
    "shiny_symbol": {
        "path": "Media/SV_Images/Shiny_Symbol.png",
        "roi": (1106, 58, 121, 34)
    },
    "box_highlighted": {
        # box 1 is 602, 143. box 2 is 682, 143. box 9 is 602, 223. box roi is 80x80
        "color": (33, 213, 227),
        "roi": (602, 143, 80, 80),
        "positions": [
            (672, 149),
            (672, 215),
            (610, 149),
            (610, 215)
        ]
    },
    "text_box": {
        "color": (12, 212, 242),
        "positions": [
            (326, 525),
            (954, 648)
        ]
    },

}

LZA_STATES = {
    # screens
    "title_screen": {
        "color": (255, 255, 254),
        "positions": [(469, 444), (663, 446), (562, 292)],
        "tol": 10,
    },
    "loading_screen": {
        "color": (54, 45, 6),
        "positions": [(527, 277), (787, 278), (631, 280)],
        "tol": 10,
    },
    "backup_screen": {
        "color": (71, 51, 52),
        "positions": [
            (768, 486),
            (505, 491),
            (654, 453),
            (446, 455)
        ]
    },
    "map_screen": {
        "color": (251, 253, 252),
        "positions": [(93, 42), (114, 42), (136, 39), (160, 41)],
        "tol": 10,
    },
    "box_screen": {
        "color": (255, 255, 254),
        "positions": [
            (290, 27),
            (259, 34),
            (242, 33),
            (223, 39),
            (191, 40)
        ]
    },
    "donut_screen": {
        "color": (237, 249, 248),
        "positions": [
            (461, 86),
            (231, 72),
            (43, 109)
        ]
    },
    # in game
    "multi_select": {
        "color": (243, 227, 54),
        "positions": [
            (126, 697),
            (129, 694),
            (123, 690)
        ]
    },
    "pokemon_in_box": {
        "color": (255, 255, 254),
        "positions": [
            (972, 91),
            (824, 104),
            (743, 85)
        ]
    },
    "shiny_symbol": {
        "path": "Media/LZA_Images/Shiny_Symbol.png",
        "roi": (1045, 82, 42, 22)
    },
    "text_box": {
        "color": (239, 238, 239),
        "positions": [
            (329, 680),
            (341, 574),
            (916, 572)
        ]
    },
    "donut_results": {
        "color": (238, 253, 251),
        "positions": [
            (93, 649),
            (729, 664),
            (731, 457),
            (94, 453)
        ]
    },
    # rois
    "donut_powers_rois": [
        (172, 552, 250, 24),
        (172, 584, 250, 24),
        (172, 616, 250, 24)
    ],
    "map_screen_rois": [
        (42, 179, 370, 43),
        (42, 235, 370, 43),
        (42, 289, 370, 43),
        (42, 345, 370, 43),
        (42, 401, 370, 43),
        (42, 457, 370, 43), 
        (42, 513, 370, 43),
    ],
    "berry_select_rois": [
        (22, 182, 289, 49),
        (22, 244, 289, 49),
        (22, 306, 289, 49),
        (22, 368, 289, 49),
        (22, 430, 289, 49),
        (22, 492, 289, 49),
        (22, 554, 289, 49),
        (22, 616, 289, 49)
    ],
    # program specific
}

# Map a game string to its state dict
GAME_STATES = {
    "GENERIC": GENERIC_STATES,
    "SWSH": SWSH_STATES,
    "BDSP": BDSP_STATES,
    "LA": LA_STATES,
    "SV": SV_STATES,
    "LZA": LZA_STATES,
}

TEXT = {
    "DONUT_POWER_OPTIONS": [
        "Sour:",
        "Item Power: Berries",
        "Item Power: Special",
        "Item Power: Poké Balls",
        "Item Power: Candies",
        "Item Power: Coins",
        "Item Power: Treasures",
        "Big Haul Power",
        "Mega Charging Power",
        "Mega Conservation Power",
        "Sweet:",
        "Sparkling Power: All Types",
        "Alpha Power",
        "Teensy Power",
        "Humungo Power",
        "Spicy:",
        "Sp. Attack Power",
        "Attack Power",
        "Speed Power",
        "Bitter:",
        "Defense Power",
        "Sp. Defense Power",
        "Resistance Power",
    ],
    "DONUT_LEVEL_OPTIONS": [
        "1",
        "2",
        "3",
        "1-2",
        "2-3",
        "1-3",
    ],
    "PATTERNS": [
        r"\bwild\s+(.+?)\s+appeared\b",
        r"\bencountered\s+(?:a\s+)?wild\s+(.+?)(?:[.!]|$)",
        r"^(.+?)\s+hatched\s+from\s+the\s+egg\b",
        r"\bgo!?\s+(.+?)(?:[.!]|$)",
        r"^(.+?)\s+appeared\b",
    ],
    "PROGRAM_DESCRIPTIONS": {
        # SWSH
        "Static_Encounter_SWSH": {"text": "Uses a timer to find shinies.", "image": "N/A"},
        "Fossil_Reviver_SWSH": {"text": "", "image": "N/A"},
        "Egg_Hatcher_SWSH": {"text": "N/A", "image": "N/A"},
        "Pokemon_Releaser_SWSH": {"text": "N/A", "image": "N/A"},

        # BDSP
        "Static_Encounter_BDSP": {"text": "N/A", "image": "N/A"},
        "Egg_Collector_BDSP": {"text": "Stand 4 tiles to the right from the daycare man. This position is the only one that will work. The count is by box, so inputting 1 will be 30 egs, 2 is 60, etc.", "image": "N/A"},
        "Egg_Hatcher_BDSP": {"text": "Stand 4 tiles to the right from the daycare man. This position is the only one that will work. The count is by box, so inputting 1 will be 30 egs, 2 is 60, etc.", "image": "N/A"},
        "Automated_Egg_BDSP": {"text": "Stand 4 tiles to the right from the daycare man. This position is the only one that will work. The count is by box, so inputting 1 will be 30 egs, 2 is 60, etc.", "image": "N/A"},
        "Pokemon_Releaser_BDSP": {"text": "N/A", "image": "N/A"},

        # LA

        # SV
        "Pokemon_Releaser_SV": {"text": "N/A", "image": "N/A"},

        # LZA
        "Donut_Checker": {"text": "N/A", "image": "N/A"},
    },
}

COLOR_ON_SCREEN = {
    "top_left": (50, MAIN_FRAME_SIZE[1] - 50),
    "center_left": (50, MAIN_FRAME_SIZE[1] // 2 - 25),
    "bottom_left": (50, 25),
    "center": (MAIN_FRAME_SIZE[0] // 2 - 25, MAIN_FRAME_SIZE[1] // 2 - 25),
    "top_right": (MAIN_FRAME_SIZE[0] - 50, MAIN_FRAME_SIZE[1] - 50),
    "center_right": (MAIN_FRAME_SIZE[0] -50, MAIN_FRAME_SIZE[1] // 2 - 25),
    "bottom_right": (MAIN_FRAME_SIZE[0] - 50, 25),

    "home_screen": (int(MAIN_FRAME_SIZE[0] // 48 * 1), int(MAIN_FRAME_SIZE[1] // 8 * 7)),
    "health_bar": (int(MAIN_FRAME_SIZE[0] // 96 * 1), int(MAIN_FRAME_SIZE[1] // 16 * 1.6)),

    "column_height": 25,
    "small_column_height": 15,

    "black": (5,5,5),
    "white": (250, 250, 250),
    "home_color": (237, 237, 237)
}