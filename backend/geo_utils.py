# geo_utils.py

sector_to_halka = {
    "I-8/2": "NA-53",
    "G-10/3": "NA-53",
    "G-11/3": "NA-53",
    "F-10/4": "NA-52",
    "H-8/1": "NA-52",
    "G-9/1": "NA-52",
    "F-8 Markaz": "NA-52",
    "I-10/2": "NA-54",
    "I-9/1": "NA-54",
    "H-9": "NA-54",
    "G-13/1": "NA-54"
}

def get_halka_from_address(address):
    for sector, halka in sector_to_halka.items():
        if sector in address:
            return halka
    return None
