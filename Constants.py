ORIGINAL_FRAME_SIZE = (1920, 1080)
BOT_FRAME_SIZE = (1100, 570)
MAIN_FRAME_SIZE = (1280, 720)
SPAWN_POSITION = (300, 200)

TEXT_BOX = {
    'left_white': (int(MAIN_FRAME_SIZE[0] // 16 * 1.2), int(MAIN_FRAME_SIZE[1] // 16 * 1)),
    'right_white': (int(MAIN_FRAME_SIZE[0] - MAIN_FRAME_SIZE[0] // 16 * 1.2), int(MAIN_FRAME_SIZE[1] // 16 * 1))
}

SWSH_CONSTANTS = {
    'pokemon_name': (313, 395, 143, 31),
    'static_roi': (699, 244, 481, 320),
    'static_v_threshold': 230,
    'static_s_max': 80,
    'static_brightness_threshold': 80000
}

BDSP_CONSTANTS = {
    'step_roi': (620, 393, 60, 7),
    'hatchery_poke_center': (1012, 374, 268, 346),
    'nursery_man': (165, 343, 40, 54),
    'text_box_roi': (268, 591, 757, 107)
    
}

COLOR_ON_SCREEN = {
    'top_left': (50, MAIN_FRAME_SIZE[1] - 50),
    'center_left': (50, MAIN_FRAME_SIZE[1] // 2 - 25),
    'bottom_left': (50, 25),
    'center': (MAIN_FRAME_SIZE[0] // 2 - 25, MAIN_FRAME_SIZE[1] // 2 - 25),
    'top_right': (MAIN_FRAME_SIZE[0] - 50, MAIN_FRAME_SIZE[1] - 50),
    'center_right': (MAIN_FRAME_SIZE[0] -50, MAIN_FRAME_SIZE[1] // 2 - 25),
    'bottom_right': (MAIN_FRAME_SIZE[0] - 50, 25),

    'home_screen': (int(MAIN_FRAME_SIZE[0] // 48 * 1), int(MAIN_FRAME_SIZE[1] // 8 * 7)),
    'health_bar': (int(MAIN_FRAME_SIZE[0] // 96 * 1), int(MAIN_FRAME_SIZE[1] // 16 * 1.6)),

    'column_height': 25,
    'small_column_height': 15,

    'black': (5,5,5),
    'white': (250, 250, 250),
    'home_color': (237, 237, 237)
}