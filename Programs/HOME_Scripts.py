import os
import sys
import time
import serial
from Modules.Controller import Controller
from Modules.Macros import *
from Modules.Database import *
from Modules.States import *

def Sort_Home(image: Image_Processing, ctrl: Controller, state: str | None, input: int) -> str:
    """
    This sorts pokemon in to dex order. It take three inputs:
    first_sorted_box: the box where they start putting the sorted pokemon. make sure enough boxes are empty.
    start_box: the box where the program starts reading through
    end_box: the box where the program will stop reading through the pokemon
    Notice: Due to having the same name, alt forme pokemon are seen as the same:
    i.e, meowth, galarian meowth, and alolan meowth all are seen the same
    """
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