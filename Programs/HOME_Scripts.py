import os
import sys
import time
import serial
import requests 
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

BASE_API = "https://pokeapi.co/api/v2"
UA = "national-dex-home-sprites/1.0"

HOME_FRONT = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/{id}.png"
HOME_SHINY = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/{id}.png"

def PokeApi(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    return None

def Sort_Home(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    """
    This sorts pokemon in to dex order. It take Four inputs:
    first_sorted_box: the box where they start putting the sorted pokemon. make sure enough boxes are empty.
    start_box: the box where the program starts reading through
    end_box: the box where the program will stop reading through the pokemon
    sort_order: 1 is sort in national dex order, and then shiny in national dex. 2 is pokemon and shiny next to eachother
    Notice: Due to having the same name, alt forme pokemon are seen as the same:
    i.e, meowth, galarian meowth, and alolan meowth all are seen the same
    """
    CACHE_PATH = "Media/box_sort_cache.json"

    if os.path.exists(CACHE_PATH):
        cache = Persistance.load_json(CACHE_PATH)  
    return None

def Rename_Boxes(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    """
    This renames all the boxes into the inputed name. Takes 3 inputs:
    Name: what to name the boxes
    start_box: what box to start with
    end_box: what box to stop with
    """
    
def Sort_Specific_Pokemon_Types(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    """
    This sorts pokemon by type: IE, shiny, mythical, legendary, etc. Takes 3 inputs:
    Type: Types of pokemon to be sorted
    start_box: what box to start with
    end_box: what box to stop with
    """