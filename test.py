import tkinter as tk
root = tk.Tk()
root.geometry('200x120+40+40')
root.overrideredirect(True)
root.configure(bg='#181A20')
tk.Label(root, text='07:30', fg='white', bg='#181A20', font=('Segoe UI', 30)).pack(pady=20)
root.mainloop()
