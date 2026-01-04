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
    # rois
    "pokemon_name": (313, 395, 143, 31),

    # program_specific
    "static_encounter": {
        "static_roi": (999, 244, 181, 320),
        "static_v_threshold": 245,
        "static_s_max": 40,
        "static_brightness_ratio": 0.05
    }
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
    'daycare_sign': {
        "path": "Media/BDSP_Images/Day_Care_Sign.png",
        "roi": (240, 160, 180, 180)
    },
    "egg_acquired": {
        "color": (101, 234, 243),
        "positions": [(943, 141), (941, 253), (339, 270), (338, 142)],
        "tol": 10,
    },
    "egg_hatching": {
        'path': 'Media/BDSP_Images/Hatched.png',
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

SV_STATES = {}

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
    'backup_screen': {
        'color': (71, 51, 52),
        'positions': [
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
        'color': (255, 255, 254),
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
        'color': (243, 227, 54),
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
        'color': (239, 238, 239),
        'positions': [
            (329, 680),
            (341, 574),
            (916, 572)
        ]
    },
    'donut_results': {
        'color': (238, 253, 251),
        'positions': [
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

PROGRAM_META = {
    ("BDSP", "Egg_Collector_BDSP"): {
        "desc": "Stand at the Day Care man. Party must have 1 empty slot. Program will collect eggs then walk to reposition.",
        "img": "Media/Docs/BDSP_EggCollector_Setup.png",
    }
}


SWSH_CONSTANTS = {
    "pokemon_name": (313, 395, 143, 31),
    "static_roi": (999, 244, 181, 320),
    "static_v_threshold": 245,
    "static_s_max": 40,
    "static_brightness_ratio": 0.05
}

BDSP_CONSTANTS = {
    "step_roi": (620, 393, 60, 7),
    "hatchery_poke_center": (1012, 374, 268, 346),
    "nursery_man": (165, 343, 40, 54),
    "text_box_roi": (268, 591, 757, 107)
    
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