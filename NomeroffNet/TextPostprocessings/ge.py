from .xx_xx import XxXx
import string


class Ge(XxXx):
    def __init__(self) -> None:
        super().__init__()
        self.ALLOWED_LITERS = [x for x in string.ascii_letters]
        self.ALLOWED_LITERS.append("0")

        self.STANDARTS = ["@@@###", "@@###@@"]
        self.STANDART = ""

    def find(self, text: str, strong: bool = False) -> str:
        for standart in self.STANDARTS:
            self.STANDART = standart
            match = self.find_fully(text)
            if match:
                text = match.group(0)
                newtext = ""
                for i, standart_letter in enumerate(standart):
                    if standart_letter[0] == "@" and text[i] == "0":
                        newtext += "O"
                    else:
                        newtext += text[i]
                return newtext
        return text


ge = Ge()
