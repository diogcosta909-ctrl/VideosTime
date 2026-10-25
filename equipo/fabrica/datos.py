"""Datos reales del libro 'Aprende a leer y escribir con Pinti' (abecedario pág. 5, páginas de letras y sílabas)."""
# letra: (palabra, nº de ilustración pag05_0NN, página de la letra, página de sílabas o None, sonido que se enseña, sílabas)
# El sonido nunca es el nombre de la letra: es lo que se oye al empezar la palabra.
LETRAS = {
    "a": ("abeja", 9, 14, None, "aaa", None), "e": ("estrella", 13, 15, None, "eee", None),
    "i": ("iglú", 17, 16, None, "iii", None), "o": ("oso", 24, 17, None, "ooo", None),
    "u": ("uvas", 30, 18, None, "uuu", None),
    "b": ("barco", 10, 44, 45, "ba", ["ba", "be", "bi", "bo", "bu"]),
    "c": ("casa", 11, 42, 43, "ca", None),
    "d": ("dado", 12, 32, 33, "da", ["da", "de", "di", "do", "du"]),
    "f": ("foco", 14, 37, 38, "fa", ["fa", "fe", "fi", "fo", "fu"]),
    "g": ("gato", 15, 48, 49, "ga", None),
    "h": ("helado", 16, 60, 61, "", ["ha", "he", "hi", "ho", "hu"]),
    "j": ("jugo", 18, 50, 51, "ja", ["ja", "je", "ji", "jo", "ju"]),
    "k": ("kiwi", 19, 65, 66, "ki", None),
    "l": ("luna", 20, 25, 26, "la", ["la", "le", "li", "lo", "lu"]),
    "m": ("mamá", 21, 20, 21, "ma", ["ma", "me", "mi", "mo", "mu"]),
    "n": ("nube", 22, 34, 35, "na", ["na", "ne", "ni", "no", "nu"]),
    "ñ": ("piña", 23, 54, 55, "ña", ["ña", "ñe", "ñi", "ño", "ñu"]),
    "p": ("papá", 25, 23, 24, "pa", ["pa", "pe", "pi", "po", "pu"]),
    "q": ("queso", 26, 62, 63, "ke", None),
    "r": ("regalo", 27, 39, 40, "ra", ["ra", "re", "ri", "ro", "ru"]),
    "s": ("sol", 28, 27, 28, "sa", ["sa", "se", "si", "so", "su"]),
    "t": ("tomate", 29, 30, 31, "ta", ["ta", "te", "ti", "to", "tu"]),
    "v": ("vela", 31, 46, 47, "va", ["va", "ve", "vi", "vo", "vu"]),
    "y": ("yoyo", 34, 56, 57, "ya", ["ya", "ye", "yi", "yo", "yu"]),
    "z": ("zapato", 35, 58, 59, "sa", ["za", "ze", "zi", "zo", "zu"]),
}
ORDEN = list(LETRAS)

# Ganchos (voz y pantalla a la vez). LATAM neutro, sin precio, sin "peque", sin nombrar letras en voz.
GANCHOS_LETRA = [
    "¿Con qué sonido empieza {palabra}?",
    "¿Tu niño sabe cómo empieza {palabra}?",
    "Juega a adivinar: ¿cómo empieza {palabra}?",
    "{Palabra}: ¿con qué suena al empezar?",
]
GANCHOS_SILABAS = [
    "Cinco sílabas para leer hoy",
    "Que tu niño lea estas cinco sílabas",
    "Sílabas fáciles para empezar a leer",
    "¿Sabe leer estas cinco sílabas?",
]
CIERRE_VOZ = "Libro imprimible, de 3 a 6 años."
CIERRE_TEXTO = "Libro imprimible · 3 a 6 años"
FONDOS = ["crema", "cuarto", "mesa", "cielo"]
