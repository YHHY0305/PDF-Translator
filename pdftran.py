import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont
import fitz  # PyMuPDF
from PIL import Image, ImageTk
import requests
import json
import threading
try:
    import markdown as mdlib
except Exception:
    mdlib = None
try:
    from tkinterweb import HtmlFrame
except Exception:
    HtmlFrame = None
import translators as ts


class PDFTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Translator")

        # 分隔左右面板
        self.pane = tk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.pane.pack(fill=tk.BOTH, expand=True)

        # 左侧：PDF显示区 (Canvas支持滚动和选取)
        self.left_frame = tk.Frame(self.pane)
        self.canvas = tk.Canvas(self.left_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.pane.add(self.left_frame, stretch="always")

        # 右侧：翻译区
        self.right_frame = tk.Frame(self.pane)
        # 翻译模式选择：普通翻译 / LLM 翻译
        trans_bar = tk.Frame(self.right_frame)
        tk.Label(trans_bar, text="翻译模式:").pack(side=tk.LEFT)
        self.translate_mode_var = tk.StringVar(value='llm')
        tk.Radiobutton(trans_bar, text="普通翻译", variable=self.translate_mode_var, value='normal').pack(side=tk.LEFT)
        tk.Radiobutton(trans_bar, text="LLM翻译", variable=self.translate_mode_var, value='llm').pack(side=tk.LEFT, padx=6)
        self.render_md_var_tr = tk.BooleanVar(value=False)
        tk.Checkbutton(trans_bar, text="Markdown渲染", variable=self.render_md_var_tr, command=self._refresh_translation_render).pack(side=tk.LEFT, padx=6)
        trans_bar.pack(fill=tk.X)
        # 文本与（可选）HTML渲染，容器增加边界与内边距
        self.translate_container = tk.Frame(self.right_frame, bd=1, relief=tk.SOLID, padx=6, pady=6)
        self.translate_container.pack(fill=tk.BOTH, expand=True)
        # 字体与行距
        self.ui_font = tkfont.Font(family=("Microsoft YaHei UI", "Segoe UI", "Arial"), size=11)
        self.code_font = tkfont.Font(family=("Consolas", "Menlo", "Courier New"), size=10)
        self.translate_text = tk.Text(
            self.translate_container,
            wrap=tk.WORD,
            spacing1=6,
            spacing2=2,
            spacing3=6,
            bg="#fafafa"
        )
        try:
            self.translate_text.configure(font=self.ui_font)
        except Exception:
            pass
        self.translate_text.pack(fill=tk.BOTH, expand=True)
        self.translate_html = HtmlFrame(self.translate_container) if HtmlFrame else None
        if self.translate_html:
            self.translate_html.pack_forget()
        self.pane.add(self.right_frame, stretch="always")

        # 最右侧：LLM 对话区（Ollama）
        self.chat_frame = tk.Frame(self.pane)
        top_bar = tk.Frame(self.chat_frame)
        # Ollama 服务器配置
        server_frame = tk.Frame(top_bar)
        tk.Label(server_frame, text="服务器:").pack(side=tk.LEFT)
        self.ollama_url_var = tk.StringVar(value="http://192.168.1.135:11434")
        self.url_entry = tk.Entry(server_frame, textvariable=self.ollama_url_var, width=20)
        self.url_entry.pack(side=tk.LEFT, padx=2)
        tk.Button(server_frame, text="连接测试", command=self.test_ollama_connection).pack(side=tk.LEFT, padx=2)
        server_frame.pack(side=tk.LEFT)
        
        # 模型选择
        model_frame = tk.Frame(top_bar)
        tk.Label(model_frame, text="模型:").pack(side=tk.LEFT)
        self.ollama_model_var = tk.StringVar(value='')
        self.model_options = []
        self.model_menu = tk.OptionMenu(model_frame, self.ollama_model_var, ())
        self.model_menu.config(width=16)
        self.model_menu.pack(side=tk.LEFT)
        tk.Button(model_frame, text="刷新", command=self.refresh_ollama_models).pack(side=tk.LEFT, padx=6)
        model_frame.pack(side=tk.LEFT)
        
        self.use_translation_var = tk.BooleanVar(value=True)
        tk.Checkbutton(top_bar, text="带上下文(翻译)", variable=self.use_translation_var).pack(side=tk.RIGHT)
        top_bar.pack(fill=tk.X)

        # 对话显示（文本 + 可选 HTML 渲染）
        chat_top = tk.Frame(self.chat_frame)
        self.render_md_var_chat = tk.BooleanVar(value=False)
        tk.Checkbutton(chat_top, text="Markdown渲染", variable=self.render_md_var_chat, command=self._refresh_chat_render).pack(side=tk.RIGHT)
        chat_top.pack(fill=tk.X)
        # 内容容器：边界与内边距
        self.chat_container = tk.Frame(self.chat_frame, bd=1, relief=tk.SOLID, padx=6, pady=6)
        self.chat_container.pack(fill=tk.BOTH, expand=True)
        self.chat_display = tk.Text(
            self.chat_container,
            wrap=tk.WORD,
            state=tk.DISABLED,
            spacing1=6,
            spacing2=2,
            spacing3=6,
            bg="#fafafa"
        )
        try:
            self.chat_display.configure(font=self.ui_font)
        except Exception:
            pass
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_html = HtmlFrame(self.chat_container) if HtmlFrame else None
        if self.chat_html:
            self.chat_html.pack_forget()
        input_bar = tk.Frame(self.chat_frame)
        self.chat_entry = tk.Entry(input_bar)
        self.chat_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.chat_entry.bind("<Return>", self.on_chat_return)
        tk.Button(input_bar, text="发送", command=self.send_chat_message).pack(side=tk.LEFT, padx=6)
        input_bar.pack(fill=tk.X)

        self.pane.add(self.chat_frame, stretch="always")

        # 菜单：打开文件
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open PDF", command=self.open_pdf)
        menubar.add_cascade(label="File", menu=filemenu)
        root.config(menu=menubar)
        nav_frame = tk.Frame(self.left_frame)
        tk.Button(nav_frame, text="Prev", command=self.prev_page).pack(side=tk.LEFT)
        tk.Button(nav_frame, text="Next", command=self.next_page).pack(side=tk.LEFT)
        # 交互模式切换：选取 / 拖拽
        self.mode_var = tk.StringVar(value='select')
        tk.Radiobutton(nav_frame, text="选取", variable=self.mode_var, value='select')\
            .pack(side=tk.LEFT, padx=6)
        tk.Radiobutton(nav_frame, text="拖拽", variable=self.mode_var, value='pan')\
            .pack(side=tk.LEFT)
        nav_frame.pack()
        self.vscroll = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.config(yscrollcommand=self.vscroll.set)
        self.pdf_doc = None
        self.current_page = 0
        self.zoom = 1.0
        self.render_width = 0
        self.render_height = 0
        self.target_language = 'zh'
        self.start_x = self.start_y = 0
        self.highlight_items = []
        self.active_line_key = None  # (block, line) of current selection line
        self.active_block = None  # 起始列（block）
        self.chat_history = []  # 存储与 Ollama 的历史消息
        # 绑定 URL 变化事件
        self.ollama_url_var.trace('w', self._on_url_change)
        self.canvas.bind("<Button-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_progressive_highlight)
        self.canvas.bind("<ButtonRelease-1>", self.end_selection)
        # Windows 下 Ctrl + 滚轮缩放
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_mousewheel)

    def open_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.pdf_doc = fitz.open(file_path)
            self.show_page(0)  # 显示第一页
        # 初次加载尝试获取模型列表
        self.root.after(100, self.safe_refresh_models)

    def start_selection(self, event):
        # 根据模式决定行为：pan 记录平移起点；select 进入选择
        if getattr(self, 'mode_var', None) and self.mode_var.get() == 'pan':
            self.canvas.scan_mark(event.x, event.y)
            # 标记为平移模式
            self.pan_mode = True
            return
        else:
            self.pan_mode = False
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        # 清除上一次高亮
        if self.highlight_items:
            for item_id in self.highlight_items:
                self.canvas.delete(item_id)
            self.highlight_items = []
        # 当前拖拽会话的高亮映射（去重）
        self.current_drag_highlight = {}
        # 锁定本次选择所在的行
        if self.pdf_doc:
            page = self.pdf_doc[self.current_page]
            self.active_line_key = self._locate_line_at(page, (self.start_x, self.start_y))
            # 锁定列（block）
            if self.active_line_key is not None:
                self.active_block = self.active_line_key[0]
            else:
                self.active_block = None
        else:
            self.active_line_key = None
            self.active_block = None

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page(self.current_page)

    def next_page(self):
        if self.pdf_doc and self.current_page < len(self.pdf_doc) - 1:
            self.current_page += 1
            self.show_page(self.current_page)
    # 光标式选择：按下记录起点，松开确定终点，按词取范围

    def end_selection(self, event):
        if getattr(self, 'mode_var', None) and self.mode_var.get() == 'pan':
            # 结束平移，不进行文本选择
            self.pan_mode = False
            return
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        if self.pdf_doc:
            page = self.pdf_doc[self.current_page]
            selected_text = self._extract_text_by_cursor(page, (self.start_x, self.start_y), (end_x, end_y))
            if selected_text:
                self.translate(selected_text)
        # 结束后不再额外绘制，保留拖拽时的渐进高亮

    def translate(self, text):
        try:
            if getattr(self, 'translate_mode_var', None) and self.translate_mode_var.get() == 'llm':
                # 使用 LLM 翻译，通过 Ollama 聊天接口
                model = getattr(self, 'ollama_model_var', None).get().strip() if getattr(self, 'ollama_model_var', None) else 'llama3'
                sys_prompt = "您是一名专业翻译人员。请将用户内容准确翻译成目标语言，并仅输出翻译结果"
                messages = [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Target language: {self.target_language}.\nText: {text}"}
                ]
                # 流式输出翻译（后台线程，避免阻塞 UI）
                self._stream_translation(model, messages)
                return
            else:
                # 普通翻译（有道）
                translated = ts.translate_text(
                    query_text=text,
                    translator='youdao',
                    from_language='auto',
                    to_language=self.target_language
                )
            if translated is not None and (not (getattr(self, 'translate_mode_var', None) and self.translate_mode_var.get() == 'llm')):
                self.translate_text.delete(1.0, tk.END)
                self.translate_text.insert(tk.END, translated)
        except Exception as e:
            self.translate_text.insert(tk.END, f"Translation error: {e}")

    def show_page(self, page_num):
        # 渲染页面为图像
        page = self.pdf_doc[page_num]
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self.photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.render_width, self.render_height = pix.width, pix.height
        self.canvas.config(scrollregion=(0, 0, self.render_width, self.render_height))

        # 绑定文本选取事件（稍后实现）


    def _extract_text_by_cursor(self, page, start_xy, end_xy):
        words = self._select_words_by_drag(page, start_xy, end_xy)
        if not words:
            return ""
        words.sort(key=lambda t: (t[5], t[6], t[7], t[0]))  # by block, line, word_no, x0
        lines = []
        current_key = (words[0][5], words[0][6])
        buffer = []
        for wx0, wy0, wx1, wy1, wtext, wblock, wline, wno in words:
            key = (wblock, wline)
            if key != current_key:
                lines.append(" ".join(buffer))
                buffer = [wtext]
                current_key = key
            else:
                buffer.append(wtext)
        if buffer:
            lines.append(" ".join(buffer))
        # 不要换行，跨行以空格连接
        return " ".join(lines)

    def append_chat_line(self, prefix, text):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{prefix}{text}\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def send_chat_message(self):
        question = self.chat_entry.get().strip()
        if not question:
            return
        self.chat_entry.delete(0, tk.END)
        self.append_chat_line("你: ", question)

        # 组装上下文
        messages = []
        if self.chat_history:
            messages.extend(self.chat_history)
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant."})

        if self.use_translation_var.get():
            ctx = self.translate_text.get(1.0, tk.END).strip()
            if ctx:
                messages.append({"role": "user", "content": f"上下文(翻译文本):\n{ctx}"})
        messages.append({"role": "user", "content": question})

        model = self.ollama_model_var.get().strip() or 'llama3'
        # 流式输出回答（后台线程，避免阻塞 UI）
        self._stream_chat_answer(model, messages)
        # 维护历史
        self.chat_history = []
        # 仅保留最近一次上下文和问答，防止无限膨胀
        self.chat_history.append({"role": "system", "content": "You are a helpful assistant."})
        if self.use_translation_var.get():
            ctx = self.translate_text.get(1.0, tk.END).strip()
            if ctx:
                self.chat_history.append({"role": "user", "content": f"上下文(翻译文本):\n{ctx}"})
        self.chat_history.append({"role": "user", "content": question})

    def _ollama_chat(self, model, messages):
        url = f"{self.ollama_url_var.get().strip()}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # 兼容不同返回结构
        if isinstance(data, dict):
            msg = data.get("message") or {}
            content = msg.get("content") or data.get("content")
            if content:
                return content
        # 流式或意外结构：尝试拼接
        if isinstance(data, list):
            parts = []
            for item in data:
                msg = item.get("message") if isinstance(item, dict) else None
                if msg and isinstance(msg, dict):
                    c = msg.get("content")
                    if c:
                        parts.append(c)
            if parts:
                return "".join(parts)
        raise RuntimeError("未获取到有效的回答")

    def _ollama_chat_stream(self, model, messages, on_delta=None):
        # 使用 Ollama 流式接口逐步读取，兼容 bytes/str
        url = f"{self.ollama_url_var.get().strip()}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        headers = {"Accept": "text/event-stream"}
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            full_text = []
            for raw in resp.iter_lines():  # yield bytes by default
                if not raw:
                    continue
                # raw: bytes → strip and decode
                if isinstance(raw, bytes):
                    bline = raw.strip()
                    if not bline:
                        continue
                    if bline.startswith(b'data:'):
                        bline = bline[5:].strip()
                    try:
                        line = bline.decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                else:
                    line = str(raw).strip()
                    if not line:
                        continue
                    if line.startswith('data:'):
                        line = line[5:].strip()
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict):
                    msg = obj.get("message") or {}
                    delta = msg.get("content")
                    if delta:
                        full_text.append(delta)
                        if on_delta:
                            on_delta(delta)
                    if obj.get("done"):
                        break
            return "".join(full_text)

    def _stream_translation(self, model, messages):
        # 在后台线程拉取流并更新翻译面板
        def run():
            try:
                chunks = []
                def on_delta(delta):
                    chunks.append(delta)
                    self.root.after(0, lambda d=delta: (
                        self.translate_text.insert(tk.END, d),
                        self.translate_text.see(tk.END)
                    ))
                # 清空 UI
                self.root.after(0, lambda: self.translate_text.delete(1.0, tk.END))
                result = self._ollama_chat_stream(model, messages, on_delta)
                # 确保 UI 与最终内容一致
                self.root.after(0, lambda r=result: (
                    self.translate_text.delete(1.0, tk.END),
                    self.translate_text.insert(tk.END, r)
                ))
            except Exception as e:
                self.root.after(0, lambda: self.translate_text.insert(tk.END, f"Translation error: {e}"))
        threading.Thread(target=run, daemon=True).start()

    def _stream_chat_answer(self, model, messages):
        # 在后台线程拉取流并更新聊天面板
        def run():
            try:
                self.root.after(0, lambda: (
                    self.chat_display.config(state=tk.NORMAL),
                    self.chat_display.insert(tk.END, "助手: "),
                    self.chat_display.see(tk.END)
                ))
                buffer = []
                def on_delta(delta):
                    buffer.append(delta)
                    self.root.after(0, lambda d=delta: (
                        self.chat_display.insert(tk.END, d),
                        self.chat_display.see(tk.END)
                    ))
                result = self._ollama_chat_stream(model, messages, on_delta)
                self.root.after(0, lambda: (
                    self.chat_display.insert(tk.END, "\n"),
                    self.chat_display.config(state=tk.DISABLED)
                ))
                # 更新历史
                def upd_hist():
                    self.chat_history = []
                    self.chat_history.append({"role": "system", "content": "You are a helpful assistant."})
                    if self.use_translation_var.get():
                        ctx = self.translate_text.get(1.0, tk.END).strip()
                        if ctx:
                            self.chat_history.append({"role": "user", "content": f"上下文(翻译文本):\n{ctx}"})
                    last_q = self.chat_entry.get().strip()
                    # last_q 已被清空，此处无法可靠获取；忽略或按 buffer 拼接
                    self.chat_history.append({"role": "assistant", "content": result})
                self.root.after(0, upd_hist)
            except Exception as e:
                self.root.after(0, lambda: (
                    self.chat_display.config(state=tk.NORMAL),
                    self.chat_display.insert(tk.END, f"调用失败: {e}\n"),
                    self.chat_display.config(state=tk.DISABLED)
                ))
        threading.Thread(target=run, daemon=True).start()

    def _draw_highlight_for_selection(self, page, start_xy, end_xy):
        # 将选择区域映射到页面坐标，找到相交单词并在画布上高亮
        sx, sy = start_xy
        ex, ey = end_xy
        page_w, page_h = page.rect.width, page.rect.height
        if self.render_width == 0 or self.render_height == 0:
            return
        scale_x = page_w / self.render_width
        scale_y = page_h / self.render_height
        inv_x = self.render_width / page_w
        inv_y = self.render_height / page_h

        x0 = min(sx, ex) * scale_x
        y0 = min(sy, ey) * scale_y
        x1 = max(sx, ex) * scale_x
        y1 = max(sy, ey) * scale_y
        sel_rect = fitz.Rect(x0, y0, x1, y1)

        words = self._select_words_by_drag(page, start_xy, end_xy)
        new_items = []
        for wx0, wy0, wx1, wy1, wtext, wblock, wline, wno in words:
            cx0 = wx0 * inv_x
            cy0 = wy0 * inv_y
            cx1 = wx1 * inv_x
            cy1 = wy1 * inv_y
            # 底部底色条（下划线式高亮）
            bar_height = max(2, (cy1 - cy0) * 0.2)
            item_id = self.canvas.create_rectangle(
                cx0, cy1 - bar_height, cx1, cy1,
                outline="",
                fill="yellow"
            )
            new_items.append(item_id)

        # 保存以便下次清除
        self.highlight_items.extend(new_items)

    def update_progressive_highlight(self, event):
        if not self.pdf_doc:
            return
        # 平移模式：拖动画布
        if getattr(self, 'mode_var', None) and self.mode_var.get() == 'pan':
            self.canvas.scan_dragto(event.x, event.y, gain=1)
            return
        self.pan_mode = False
        page = self.pdf_doc[self.current_page]
        sx, sy = self.start_x, self.start_y
        ex = self.canvas.canvasx(event.x)
        ey = self.canvas.canvasy(event.y)
        page_w, page_h = page.rect.width, page.rect.height
        if self.render_width == 0 or self.render_height == 0:
            return
        scale_x = page_w / self.render_width
        scale_y = page_h / self.render_height
        inv_x = self.render_width / page_w
        inv_y = self.render_height / page_h

        x0 = min(sx, ex) * scale_x
        y0 = min(sy, ey) * scale_y
        x1 = max(sx, ex) * scale_x
        y1 = max(sy, ey) * scale_y
        sel_rect = fitz.Rect(x0, y0, x1, y1)

        # 当前选择的词集合
        words = self._select_words_by_drag(page, (sx, sy), (ex, ey))
        current_keys = set((wblock, wline, wno, wx0) for wx0, wy0, wx1, wy1, wtext, wblock, wline, wno in words)

        # 全量撤销：移除所有不在当前选择范围内的高亮（跨所有已选行）
        keys_to_delete = []
        for key, item_id in list(self.current_drag_highlight.items()):
            if key not in current_keys:
                self.canvas.delete(item_id)
                if item_id in self.highlight_items:
                    self.highlight_items.remove(item_id)
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del self.current_drag_highlight[key]

        # 绘制新增的高亮
        for wx0, wy0, wx1, wy1, wtext, wblock, wline, wno in words:
            key = (wblock, wline, wno, wx0)
            if key in self.current_drag_highlight:
                continue
            cx0 = wx0 * inv_x
            cy0 = wy0 * inv_y
            cx1 = wx1 * inv_x
            cy1 = wy1 * inv_y
            bar_height = max(2, (cy1 - cy0) * 0.2)
            item_id = self.canvas.create_rectangle(
                cx0, cy1 - bar_height, cx1, cy1,
                outline="",
                fill="yellow"
            )
            self.current_drag_highlight[key] = item_id
            self.highlight_items.append(item_id)

    # 长按平移相关逻辑已由显式模式切换替代

    def _select_words_by_drag(self, page, start_xy, end_xy):
        # 依据拖动，支持跨行：起始行从起点到行尾，中间行整行，末尾行到指针处（越过行尾则整行）
        sx, sy = start_xy
        ex, ey = end_xy
        page_w, page_h = page.rect.width, page.rect.height
        if self.render_width == 0 or self.render_height == 0:
            return []
        scale_x = page_w / self.render_width
        scale_y = page_h / self.render_height
        px_start = sx * scale_x
        py_start = sy * scale_y
        px_end = ex * scale_x
        py_end = ey * scale_y

        words = page.get_text("words")
        if not words:
            return []

        # 索引按 (block, line) → 行内词，及行范围
        lines = {}
        for wx0, wy0, wx1, wy1, wtext, wblock, wline, wno in words:
            key = (wblock, wline)
            lines.setdefault(key, {"words": [], "minx": float("inf"), "maxx": float("-inf"), "y0": wy0, "y1": wy1})
            rec = lines[key]
            rec["words"].append((wx0, wy0, wx1, wy1, wtext, wblock, wline, wno))
            rec["minx"] = min(rec["minx"], wx0)
            rec["maxx"] = max(rec["maxx"], wx1)
            rec["y0"] = min(rec["y0"], wy0)
            rec["y1"] = max(rec["y1"], wy1)
        # 行序（按 y0 排序）
        ordered_line_keys = sorted(lines.keys(), key=lambda k: (lines[k]["y0"], lines[k]["minx"]))

        # 定位起止行
        start_line = self._locate_line_at(page, (sx, sy))
        end_line = self._locate_line_at(page, (ex, ey))
        if start_line is None:
            return []
        if end_line is None:
            end_line = start_line

        # 获取行索引
        def line_index(key):
            try:
                return ordered_line_keys.index(key)
            except ValueError:
                return -1

        s_idx = line_index(start_line)
        e_idx = line_index(end_line)
        if s_idx == -1:
            return []
        if e_idx == -1:
            e_idx = s_idx

        # 只能向下选取：若向上，则限制在起始行（不跨行）
        if e_idx < s_idx:
            e_idx = s_idx
            # 不强制交换 x；保持同一行内左右选择允许

        selected = []
        # 若限定列（block），先过滤可用的行键
        if self.active_block is not None:
            ordered_line_keys = [k for k in ordered_line_keys if k[0] == self.active_block]
            # 同步更新索引
            try:
                s_idx = ordered_line_keys.index(start_line)
            except ValueError:
                return []
            try:
                e_idx = ordered_line_keys.index(end_line)
            except ValueError:
                e_idx = s_idx

        # 起始行
        s_rec = lines[start_line]
        for w in sorted(s_rec["words"], key=lambda t: t[0]):
            wx0, wy0, wx1, wy1, wtext, wblock, wline, wno = w
            if e_idx == s_idx:
                # 同一行：x 范围内
                if (wx1 >= min(px_start, px_end)) and (wx0 <= max(px_start, px_end)):
                    selected.append(w)
            else:
                # 跨行：起始行从起点到行尾
                if wx1 >= px_start:
                    selected.append(w)

        # 中间整行
        for i in range(s_idx + 1, e_idx):
            key = ordered_line_keys[i]
            selected.extend(lines[key]["words"])

        # 末尾行
        if e_idx != s_idx:
            e_rec = lines[end_line]
            # 若拖到行尾以外，则整行
            line_end_x = e_rec["maxx"]
            if px_end >= line_end_x:
                selected.extend(e_rec["words"])
            else:
                for w in sorted(e_rec["words"], key=lambda t: t[0]):
                    wx0, wy0, wx1, wy1, wtext, wblock, wline, wno = w
                    if wx0 <= px_end:
                        selected.append(w)

        return selected

    def _locate_line_at(self, page, xy):
        # 根据点击位置确定所在的 (block, line)
        cx, cy = xy
        page_w, page_h = page.rect.width, page.rect.height
        if self.render_width == 0 or self.render_height == 0:
            return None
        scale_x = page_w / self.render_width
        scale_y = page_h / self.render_height
        px = cx * scale_x
        py = cy * scale_y
        words = page.get_text("words")
        best = None
        best_dist = float('inf')
        for w in words:
            wx0, wy0, wx1, wy1, wtext, wblock, wline, wno = w
            if wy0 <= py <= wy1 and wx0 <= px <= wx1:
                return (wblock, wline)
            # 垂直距离最近的行
            center_y = (wy0 + wy1) / 2
            dist = abs(center_y - py)
            if dist < best_dist:
                best_dist = dist
                best = (wblock, wline)
        return best

    def on_ctrl_mousewheel(self, event):
        # 记录光标在内容中的相对位置
        mouse_x = self.canvas.canvasx(event.x)
        mouse_y = self.canvas.canvasy(event.y)
        rel_x = 0 if self.render_width == 0 else mouse_x / max(1, self.render_width)
        rel_y = 0 if self.render_height == 0 else mouse_y / max(1, self.render_height)

        if event.delta > 0:
            self.zoom *= 1.1
        else:
            self.zoom /= 1.1
        self.zoom = max(0.2, min(5.0, self.zoom))

        # 重新渲染并尽量保持视图相对位置
        self.show_page(self.current_page)
        if self.render_width > 0 and self.render_height > 0:
            self.canvas.xview_moveto(max(0.0, min(1.0, rel_x)))
            self.canvas.yview_moveto(max(0.0, min(1.0, rel_y)))

    def on_chat_return(self, event):
        self.send_chat_message()
        return "break"

    def _markdown_to_html(self, content: str) -> str:
        if not content:
            return "<html><body></body></html>"
        try:
            if mdlib:
                html_body = mdlib.markdown(content, extensions=[
                    'fenced_code', 'tables', 'toc', 'codehilite'
                ])
            else:
                # 简单回退：仅替换换行和基本转义
                import html
                html_body = html.escape(content).replace('\n', '<br/>')
        except Exception:
            import html
            html_body = html.escape(content).replace('\n', '<br/>')
        style = "body{font-family:Segoe UI,Microsoft YaHei,Arial;font-size:13px;} code,pre{font-family:Consolas,Menlo,monospace;font-size:12px;white-space:pre;} table{border-collapse:collapse;} td,th{border:1px solid #ccc;padding:4px;}"
        return f"<html><head><meta charset='utf-8'><style>{style}</style></head><body>{html_body}</body></html>"

    def _refresh_translation_render(self):
        if not self.translate_html:
            return
        if self.render_md_var_tr.get():
            text = self.translate_text.get(1.0, tk.END)
            html = self._markdown_to_html(text)
            self.translate_html.load_html(html)
            self.translate_text.pack_forget()
            self.translate_html.pack(fill=tk.BOTH, expand=True)
        else:
            if self.translate_html:
                self.translate_html.pack_forget()
            self.translate_text.pack(fill=tk.BOTH, expand=True)

    def _refresh_chat_render(self):
        if not self.chat_html:
            return
        if self.render_md_var_chat.get():
            text = self.chat_display.get(1.0, tk.END)
            html = self._markdown_to_html(text)
            self.chat_html.load_html(html)
            self.chat_display.pack_forget()
            self.chat_html.pack(fill=tk.BOTH, expand=True)
        else:
            if self.chat_html:
                self.chat_html.pack_forget()
            self.chat_display.pack(fill=tk.BOTH, expand=True)

    def safe_refresh_models(self):
        try:
            self.refresh_ollama_models()
        except Exception:
            pass

    def refresh_ollama_models(self):
        # 从 /api/tags 拉取模型列表
        url = f"{self.ollama_url_var.get().strip()}/api/tags"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        names = []
        if isinstance(data, dict):
            # 结构: {"models": [{"name": "qwen2:7b", ...}, ...]}
            models = data.get("models") or []
            for m in models:
                name = m.get("name")
                if name:
                    names.append(name)
        elif isinstance(data, list):
            # 兼容直接列表
            for m in data:
                if isinstance(m, dict) and m.get("name"):
                    names.append(m["name"])
        if not names:
            names = ['llama3']
        self.model_options = names
        # 更新下拉菜单
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        for name in names:
            menu.add_command(label=name, command=tk._setit(self.ollama_model_var, name))
        # 设置当前值
        if not self.ollama_model_var.get() and names:
            self.ollama_model_var.set(names[0])

    def _on_url_change(self, *args):
        # URL 变化时自动刷新模型列表
        self.root.after(500, self.safe_refresh_models)  # 延迟500ms避免频繁请求

    def test_ollama_connection(self):
        # 测试 Ollama 连接
        try:
            url = f"{self.ollama_url_var.get().strip()}/api/tags"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            tk.messagebox.showinfo("连接成功", f"已成功连接到 Ollama 服务器\n{self.ollama_url_var.get()}")
        except Exception as e:
            tk.messagebox.showerror("连接失败", f"无法连接到 Ollama 服务器\n{self.ollama_url_var.get()}\n错误: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFTranslatorApp(root)
    root.mainloop()

    
    