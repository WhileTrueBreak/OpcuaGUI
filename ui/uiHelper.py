from ui.elements.uiButton import UiButton
from ui.elements.uiText import UiText
from ui.elements.uiToggleButton import UiToggleButton
from ui.constraintManager import *

def centeredTextButton(window, constraints):
    btn = UiButton(window, constraints,)

    textConstraints = [
        COMPOUND(RELATIVE(T_X, -0.5, T_W), RELATIVE(T_X, 0.5, P_W)),
        COMPOUND(RELATIVE(T_Y, -0.5, T_H), RELATIVE(T_Y, 0.5, P_H))
    ]
    text = UiText(window, textConstraints)
    text.setLinkedElement(btn)
    btn.addChild(text)
    return (btn, text)

def centeredTextToggleButton(window, constraints):
    btn = UiToggleButton(window, constraints,)

    textConstraints = [
        COMPOUND(RELATIVE(T_X, -0.5, T_W), RELATIVE(T_X, 0.5, P_W)),
        COMPOUND(RELATIVE(T_Y, -0.5, T_H), RELATIVE(T_Y, 0.5, P_H))
    ]
    text = UiText(window, textConstraints)
    text.setLinkedElement(btn)
    btn.addChild(text)
    return (btn, text)


