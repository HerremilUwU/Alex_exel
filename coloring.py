import json
import datetime
import time
import pytz
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys
import locale

# === ✅ Konfiguration laden ===
CONFIG_DIR = "C:\\Users\\gamin\\OneDrive\\Dokumente"
if CONFIG_DIR not in sys.path:
    sys.path.append(CONFIG_DIR)

try:
    from config_alex import SPREADSHEET_ID # pyright: ignore[reportMissingImports]
except ImportError:
    print("❌ Konfigurationsdatei 'config_alex.py' nicht gefunden!")
    exit()

# #green
green_red = 0.7137254901960784
green_green = 0.8431372549019608
green_blue = 0.6588235294117647

#red
red_red = 0.9176470588235294
red_green = 0.6
red_blue = 0.6               

#gelb
yellow_red = 1.0
yellow_green = 0.9490196078431372
yellow_blue = 0.8
def Weekday_color(row_index):
    today = datetime.datetime.now()
    weekday = today.strftime("%A")

    start_row = row_index
    end_row = row_index + 1

    if weekday in ["Dienstag", "Donnerstag"]:
        color = {"red": 1, "green": 0.6, "blue": 0.2}  # Orange
    elif weekday in ["Sonntag"]:
        color = {"red": 0.5568627450980392, "green": 0.48627450980392156, "blue": 0.7647058823529411}  # Blau
    elif weekday in ["Montag", "Mittwoch", "Freitag", "Samstag"]:
        color = {"red": 0.8509803921568627, "green": 0.8235294117647058, "blue": 0.9137254901960784}  # Standardfarbe (Lila/Weiß)

    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": start_row,
                                "endRowIndex": end_row,
                                "startColumnIndex": 0,
                                "endColumnIndex": 1
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": f"=LEN(A{row_index+1})>0"}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def offday_color(row_index):
    return {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": 2,  # C
                        "endColumnIndex": 14 # N
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {"red": 0.6, "green": 0.6, "blue": 0.6}
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
def session_color(row_index, totals_for_print):
    if any(t < 2 or t > 5 for t in totals_for_print):
        color = {"red": red_red, "green": red_green, "blue": red_blue}
    else:
        color = {"red": green_red, "green": green_green, "blue": green_blue}

    return {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": 3,  # D
                        "endColumnIndex": 4
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }

def clear_row_background(service, row_index):
    clear_request = {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=clear_request
    ).execute()
def champion2_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 7,  # Spalte H
                                "endColumnIndex": 8
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": green_red,
                                    "green": green_green,
                                    "blue": green_blue
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def I_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 8,  # Spalte I
                                "endColumnIndex": 9
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": yellow_red,
                                    "green": yellow_green,
                                    "blue": yellow_blue
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }

def color_golddiff_color(row_index, gold_diff):
    if gold_diff < 0:
        color = {"red": red_red, "green": red_green, "blue": red_blue}  # Rot
    elif gold_diff < 2000:
        color = {"red": yellow_red, "green": yellow_green, "blue": yellow_blue}  # Gelb
    else:
        color = {"red": green_red, "green": green_green, "blue": green_blue}  # Grün

    return {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": row_index,
                        "endRowIndex": row_index + 1,
                        "startColumnIndex": 12,  # Spalte L
                        "endColumnIndex": 13
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": color
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor"
                }
            }
        ]
    }

def JK(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 9,  # Spalte J
                                "endColumnIndex": 11
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.8352941176470589,
                                    "green": 0.6509803921568628,
                                    "blue": 0.7411764705882353
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }

def N_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 13,  # Spalte N
                                "endColumnIndex": 14
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.4,
                                    "green": 0.4,
                                    "blue": 0.4
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def E_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 4,  # Spalte E
                                "endColumnIndex": 5
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.788235294117647,
                                    "green": 0.8549019607843137,
                                    "blue": 0.9725490196078431
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def played_matches_color(row_index, matches):
    played_matches = len(matches)
    if played_matches < 3:
        color = {"red": red_red, "green": red_green, "blue": red_blue}  # Rot
    elif played_matches < 5:
        color = {"red": yellow_red, "green": yellow_green, "blue": yellow_blue}      # Gelb
    elif played_matches >= 5:
        color = {"red": green_red, "green": green_green, "blue": green_blue}  # Grün
    else:
        color = {"red": 1, "green": 1, "blue": 1}      # Weiß
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 2, # Spalte C
                                "endColumnIndex": 3
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": "=LEN(C{})>0".format(row_index+1)}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def B_color(row_index):
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 1,  # Spalte B
                                "endColumnIndex": 2
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "NOT_BLANK"  # Bedingung: Feld ist nicht leer
                            },
                            "format": {
                                "backgroundColor": {
                                    "red": 0.058823529411764705,
                                    "green": 0.403921568627451,
                                    "blue": 0.2627450980392157
                                }
                            }
                        }
                    },
                    "index": 0
                }
            }
        ]
    }
def cs_diff_color(row_index, cs_diff):
    if cs_diff < 0:
        color = {"red": red_red, "green": red_green, "blue": red_blue}  # Rot
    elif cs_diff < 100:
        color = {"red": yellow_red, "green": yellow_green, "blue": yellow_green}      # Gelb
    else:
        color = {"red": 0.2, "green": 1, "blue": 0.2}  # Grün
    return {
        "requests": [
            {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [
                            {
                                "sheetId": 0,
                                "startRowIndex": row_index,
                                "endRowIndex": row_index + 1,
                                "startColumnIndex": 11, # Spalte L
                                "endColumnIndex": 12
                            }
                        ],
                        "booleanRule": {
                            "condition": {
                                "type": "CUSTOM_FORMULA",
                                "values": [
                                    {"userEnteredValue": "=LEN(L{})>0".format(row_index+1)}
                                ]
                            },
                            "format": {"backgroundColor": color}
                        }
                    },
                    "index": 0
                }
            }
        ]
    }