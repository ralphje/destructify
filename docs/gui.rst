================
GUI & Hex Viewer
================

The Destructify GUI is a method to easily analyze raw binary data, and how it is handled by the structures you have
defined.

Using the GUI is very easy::

    import destructify
    from mylib import MyStructure

    with open("mydata.bin", "rb") as f:
        destructify.gui.show(MyStructure, f)

You can also use the command-line launcher::

    python -m destructify.gui mylib.MyStructure mydata.bin

.. hint::

   It is best to provide a dotted path to the location where your structure resides. You can also use ``-f`` to
   provide a path to the source file containing the structure.

The following screenshot shows how this might look if you are parsing a PNG file:

.. image:: gui.png
