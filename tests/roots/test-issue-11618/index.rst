.. role:: summaryline
.. role:: sl(summaryline)
   :class: summaryline
.. role:: signature
.. role:: sg(signature)
   :class: signature

pygame.key
==========

.. module:: pygame.key

| :sl:`pygame module to work with the keyboard`

.. function:: get_focused

   | :sl:`true if the display is receiving keyboard input from the system`
   | :sg:`get_focused() -> bool`

.. function:: get_pressed

   | :sl:`get the state of all keyboard buttons`
   | :sg:`get_pressed() -> bools`

.. function:: get_mods

   | :sl:`determine which modifier keys are being held`
   | :sg:`get_mods() -> int`

.. function:: set_mods

   | :sl:`temporarily set which modifier keys are pressed`
   | :sg:`set_mods(int) -> None`

.. function:: set_repeat

   | :sl:`control how held keys are repeated`
   | :sg:`set_repeat() -> None`
   | :sg:`set_repeat(delay) -> None`
   | :sg:`set_repeat(delay, interval) -> None`

.. function:: get_repeat

   | :sl:`see how held keys are repeated`
   | :sg:`get_repeat() -> (delay, interval)`

.. function:: name

   | :sl:`get the name of a key identifier`
   | :sg:`name(key, use_compat=True) -> str`

.. function:: key_code

   | :sl:`get the key identifier from a key name`
   | :sg:`key_code(name=string) -> int`

.. function:: start_text_input

   | :sl:`start handling Unicode text input events`
   | :sg:`start_text_input() -> None`

.. function:: stop_text_input

   | :sl:`stop handling Unicode text input events`
   | :sg:`stop_text_input() -> None`

.. function:: set_text_input_rect

   | :sl:`controls the position of the candidate list`
   | :sg:`set_text_input_rect(Rect) -> None`
