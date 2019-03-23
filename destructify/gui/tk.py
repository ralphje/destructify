import bisect
import io
import string
import tkinter
import tkinter.ttk

from destructify import ParsingContext, Structure


PRINTABLE_BYTES = (string.digits + string.ascii_letters + string.punctuation + ' ').encode("ascii")
BYTE_VALUE_STRING_MAX_LENGTH = 15


def fill_tree_with_values_recursively(tree, parent_tree_id, valuedata, position, byte_position_to_tree_index):
    if isinstance(valuedata, dict):
        # non-leaf element
        for name, (value, size) in valuedata.items():
            tree_id = tree.insert(parent_tree_id, "end", text=name, tags=("with_select_handler",))
            tree.set(tree_id, "position", position)
            tree.set(tree_id, "length", size)

            # Fill the byte_position_to_tree_index map before the recursive call, so that the deepest item has priority.
            byte_position_to_tree_index[position] = tree_id

            fill_tree_with_values_recursively(tree, tree_id, value, position, byte_position_to_tree_index)

            position += size
    else:
        # leaf element
        if isinstance(valuedata, bytes):
            valuestring = str(valuedata[:BYTE_VALUE_STRING_MAX_LENGTH])[2:-1]
            if len(valuedata) > BYTE_VALUE_STRING_MAX_LENGTH:
                valuestring += "..."
        else:
            valuestring = str(valuedata)
        tree.set(parent_tree_id, "value", valuestring)


class TkStructViewer:
    current_hover_tree_id = None

    def __init__(self, values, bytedata):
        self.bytedata = bytedata

        self.setup_ui()
        self.initialize_treeview(values)
        self.initialize_hexview()

    def initialize_treeview(self, values):
        self.tree.delete(*self.tree.get_children())
        byte_position_to_tree_index = {}
        fill_tree_with_values_recursively(self.tree, "", values, 0, byte_position_to_tree_index)
        self.byte_position_to_tree_index = sorted(byte_position_to_tree_index.items())

    def initialize_hexview(self):
        self.text.configure(state="normal")  # make text editable

        self.text.delete("1.0", "end")
        for i in range(0, len(self.bytedata), 16):
            bytes1 = " ".join(f"{v:02x}" for v in self.bytedata[i:i+8])
            bytes2 = " ".join(f"{v:02x}" for v in self.bytedata[i+8:i+16])
            ascii_repr = "".join(chr(v) if v in PRINTABLE_BYTES  else '.' for v in self.bytedata[i:i+16])
            row = f"{i:08x}  {bytes1:23}  {bytes2:23}  |{ascii_repr}|"
            self.text.insert("end", row+"\n")

        self.text.configure(state="disabled")

    def setup_ui(self):
        root = tkinter.Tk()
        content = tkinter.ttk.Frame(root)

        # text widget containing the flat representation
        text = tkinter.Text(content, wrap=tkinter.WORD)
        scroll1 = tkinter.Scrollbar(content, command=text.yview)
        text.configure(yscrollcommand=scroll1.set)
        text.tag_configure("highlight", background="lightblue")
        text.tag_configure("highlighthover", background="orange")
        text.tag_raise("sel")  # Give the selection style 'sel' highest priority
        text.bind("<Button-1>", self.on_text_clicked)
        text.bind("<Motion>", self.on_text_hover)
        text.bind("<Leave>", self.on_text_leave)
        text.configure(cursor="hand2")

        # tree widget containing the logical representation
        tree = tkinter.ttk.Treeview(content, columns=("value", "position", "length"))
        scroll2 = tkinter.Scrollbar(content, command=tree.yview)
        tree.configure(yscrollcommand=scroll2.set)
        tree.heading("value", text="Value")
        tree.heading("position", text="Position")
        tree.heading("length", text="Length")
        # Bind Release instead of normal events as otherwise the focused tree id is not updated yet.
        tree.tag_bind("with_select_handler", "<ButtonRelease-1>", self.on_tree_item_changed)
        tree.tag_bind("with_select_handler", "<KeyRelease>", self.on_tree_item_changed)

        # configure sticky-ness to specify how a widget grows when resizing
        content.grid(column=0, row=0, sticky="NSEW")
        text.grid(column=0, row=0, sticky="NSEW")
        scroll1.grid(column=1, row=0, sticky="NS")
        tree.grid(column=2, row=0, sticky="NSEW")
        scroll2.grid(column=3, row=0, sticky="NS")

        # configure the proportions of all the widgets
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1)
        content.columnconfigure(2, weight=1)
        content.rowconfigure(0, weight=1)

        # override default linux style
        root.style = tkinter.ttk.Style()
        if "clam" in root.style.theme_names():
            root.style.theme_use("clam")

        menubar = tkinter.Menu(root, tearoff=0)
        menubar.add_command(label="Copy bytes (hex)", command=self.on_copy_bytes_hex_clicked)
        menubar.add_command(label="Copy value", command=self.on_copy_value_clicked)
        root.config(menu=menubar)

        root.bind("<Control-c>", self.on_copy_bytes_hex_clicked)
        root.bind("<Control-b>", self.on_copy_value_clicked)

        self.root = root
        self.text = text
        self.tree = tree

    def add_tag_to_text_corresponding_to_tree_id(self, tree_id, tag, see=False):
        position = self.tree.set(tree_id, "position")
        length = self.tree.set(tree_id, "length")

        # end position is inclusive
        endposition = position + length - 1
        bytes_per_row = 16

        rowstart = position // bytes_per_row
        colstart = position % bytes_per_row
        rowend = endposition // bytes_per_row
        colend = endposition % bytes_per_row

        # row: 8-hex 2-space 23-ascii 2-space 23-ascii 2-space pipe 16-ascii pipe
        ascii_start = 8+2+23+2+23+2+1
        bytesstart = 8+2

        for r in range(rowstart, rowend+1):
            curcolstart = colstart if r == rowstart else 0
            curcolend = colend if r == rowend else (bytes_per_row-1)

            colcoordstart = bytesstart + curcolstart*3 + (1 if curcolstart >= 8 else 0)
            colcoordend = bytesstart + curcolend*3 + 2 + (1 if curcolend >= 8 else 0)

            # highlight hexadecimal representation
            self.text.tag_add(tag, f"{r+1}.{colcoordstart}", f"{r+1}.{colcoordend}")
            # highlight ascii representation
            self.text.tag_add(tag, f"{r+1}.{ascii_start+curcolstart}", f"{r+1}.{ascii_start+curcolend+1}")

        if see:
            self.text.see(f"{rowstart+1}.0")

    def get_tree_id_from_mouse_event(self, ev):
        text_index = self.text.index(f"@{ev.x},{ev.y}")
        r, c = (int(v) for v in text_index.split("."))

        # row: 8-hex 2-space 23-ascii 2-space 23-ascii 2-space pipe 16-ascii pipe
        if 10 <= c < 10+23+2+23:
            bytecol = (c - 10 - (1 if c > 34 else 0)) // 3
        elif 8+2+23+2+23+2+1 <= c < 8+2+23+2+23+2+1+16:
            bytecol = c-8-2-23-2-23-2-1
        else:
            return None

        byte_index = (r-1)*16 + bytecol

        # As (v,) < (v, n) for all n, we search for the value less than (byteindex+1,)
        # since that will be our current item in the byte_position_to_tree_index map.
        # See also: https://docs.python.org/3.7/library/bisect.html#searching-sorted-lists
        i = bisect.bisect_left(self.byte_position_to_tree_index, (byte_index+1,))
        return self.byte_position_to_tree_index[i-1][1]

    def on_tree_item_changed(self, ev):
        selected_tree_id = self.tree.focus()
        self.text.tag_remove("highlight", "1.0", "end")
        self.add_tag_to_text_corresponding_to_tree_id(selected_tree_id, "highlight", see=True)

    def on_text_clicked(self, ev):
        tree_id = self.get_tree_id_from_mouse_event(ev)
        if tree_id is None:
            return

        # Expand all parent tree items to view the selected item
        tree_id_to_open = tree_id
        while tree_id_to_open != "":
            self.tree.item(tree_id_to_open, open=True)
            tree_id_to_open = self.tree.parent(tree_id_to_open)
        self.tree.selection_set(tree_id)
        self.tree.focus(tree_id)
        self.tree.see(tree_id)

        self.text.tag_remove("highlight", "1.0", "end")
        self.add_tag_to_text_corresponding_to_tree_id(tree_id, "highlight")

    def on_text_hover(self, ev):
        tree_id = self.get_tree_id_from_mouse_event(ev)
        if tree_id != self.current_hover_tree_id:
            self.current_hover_tree_id = tree_id
            self.text.tag_remove("highlighthover", "1.0", "end")
            if tree_id is None:
                return
            self.add_tag_to_text_corresponding_to_tree_id(tree_id, "highlighthover")

    def on_text_leave(self, ev):
        if self.current_hover_tree_id is not None:
            self.text.tag_remove("highlighthover", "1.0", "end")
            self.current_hover_tree_id = None

    def on_copy_bytes_hex_clicked(self, event=None):
        selected_tree_id = self.tree.focus()
        field_position = self.tree.set(selected_tree_id, "position")
        field_length = self.tree.set(selected_tree_id, "length")
        selected_bytes = self.bytedata[field_position:field_position+field_length]

        self.root.clipboard_clear()
        self.root.clipboard_append(selected_bytes.hex())

    def on_copy_value_clicked(self, event=None):
        selected_tree_id = self.tree.focus()
        field_value = self.tree.set(selected_tree_id, "value")

        self.root.clipboard_clear()
        self.root.clipboard_append(field_value)

    def run(self):
        self.root.mainloop()


def destructify_context_to_dict(context):
    res = {}
    for name, field in context.fields.items():
        if type(name) == int:
            name = f"[{name}]"
        if field.subcontext is not None:
            res[name] = (destructify_context_to_dict(field.subcontext), field.length)
        else:
            res[name] = (field.value, field.length)
    return res


def show(structure, stream):
    if not issubclass(structure, Structure):
        raise ValueError(f"{structure!r} is not a Structure")

    if isinstance(stream, bytes):
        raw = stream
    else:
        raw = stream.read()

    context = ParsingContext(structure)
    structure.from_stream(io.BytesIO(raw), context)

    dict_representation = destructify_context_to_dict(context)

    gui = TkStructViewer(dict_representation, raw)
    gui.run()
