"""
Author: Richard Clark

Fit Matplotlib windows to the available screen on Tk and Qt backends."""


def wait_for_click(figure):
    """Wait for a mouse click, returning False if the window is closed."""
    import matplotlib.pyplot as plt

    if not plt.fignum_exists(figure.number):
        return False
    clicked = False

    def advance(event):
        nonlocal clicked
        clicked = True
        figure.canvas.stop_event_loop()

    def close(event):
        figure.canvas.stop_event_loop()

    click_id = figure.canvas.mpl_connect("button_press_event", advance)
    close_id = figure.canvas.mpl_connect("close_event", close)
    try:
        figure.canvas.draw_idle()
        figure.canvas.start_event_loop(timeout=0)
    finally:
        figure.canvas.mpl_disconnect(click_id)
        figure.canvas.mpl_disconnect(close_id)
    return clicked and plt.fignum_exists(figure.number)


def fit_window_to_screen(figure):
    manager = figure.canvas.manager
    window = getattr(manager, "window", None)
    if window is None:
        return

    if hasattr(window, "winfo_screenwidth"):  # TkAgg
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        # Leave room for window borders, the toolbar and the taskbar.
        width = min(round(figure.get_figwidth() * figure.dpi), int(screen_width * 0.85))
        height = min(round(figure.get_figheight() * figure.dpi), int(screen_height * 0.80))
        figure.set_size_inches(width / figure.dpi, height / figure.dpi)
        window.update_idletasks()
        window_width = window.winfo_reqwidth()
        window_height = window.winfo_reqheight()
        x = max(0, (screen_width - window_width) // 2)
        y = max(0, (screen_height - window_height) // 2 - 20)
        window.wm_geometry(f"+{x}+{y}")
    elif hasattr(window, "screen"):  # QtAgg
        screen = window.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width = min(window.width(), int(available.width() * 0.85))
        height = min(window.height(), int(available.height() * 0.80))
        window.resize(width, height)
        window.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )
