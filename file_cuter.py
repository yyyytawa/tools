import tkinter as tk
from tkinter import filedialog, messagebox
import os
import argparse
import sys
import json
import hashlib

# 设置文件路径
SETTINGS_FILE = "settings.json"

def split_file():
    input_file = input_file_entry.get()
    output_dir = output_dir_entry.get()
    output_prefix = output_prefix_entry.get()
    chunk_size_str = chunk_size_entry.get()
    unit = unit_var.get()
    extension = extension_entry.get()
    checksum_type = get_settings().get("checksum_type", None)

    if not input_file or not output_prefix or not chunk_size_str:
        error_label.config(text="请填写所有参数！")
        return

    try:
        chunk_size = int(chunk_size_str)
        # 处理输出目录
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)

        with open(input_file, "rb") as f_in:
            total_size = os.path.getsize(input_file)
            chunk_num = 1
            # 根据单位转换 chunk_size
            if unit == "KB":
                chunk_size *= 1024
            elif unit == "MB":
                chunk_size *= 1024 * 1024
            elif unit == "GB":
                chunk_size *= 1024 * 1024 * 1024

            checksum_list = []  # 存储校验值列表

            while True:
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                # 添加扩展名
                if extension:
                    output_file = os.path.join(output_dir, f"{output_prefix}_{chunk_num:03d}{extension}")
                else:
                    output_file = os.path.join(output_dir, f"{output_prefix}_{chunk_num:03d}")

                with open(output_file, "wb") as f_out:
                    f_out.write(chunk)
                chunk_num += 1
                print(f"已分割 {output_file} (大小: {len(chunk)} 字节)")

                # 计算校验值并添加到列表
                if checksum_type:
                    if checksum_type == "SHA256":
                        checksum = hashlib.sha256(chunk).hexdigest()
                    elif checksum_type == "MD5":
                        checksum = hashlib.md5(chunk).hexdigest()
                    checksum_list.append(checksum)

            print(f"文件 {input_file} 已成功分割成 {chunk_num} 个文件。")
            error_label.config(text=f"文件已成功分割成 {chunk_num} 个文件。")

            # 输出校验值到文件
            if checksum_list:
                checksum_filename = f"{checksum_type}sum.txt"
                checksum_filepath = os.path.join(output_dir, checksum_filename)
                with open(checksum_filepath, "w") as f_checksum:
                    for i, checksum in enumerate(checksum_list):
                        f_checksum.write(f"{checksum}  #{output_prefix}_{i+1:03d}\n")
                print(f"校验值已保存到 {checksum_filepath}")
    except FileNotFoundError:
        error_label.config(text=f"找不到文件: {input_file}")
    except ValueError:
        error_label.config(text="无效的分割大小！")
    except Exception as e:
        error_label.config(text=f"错误: {e}")

def browse_input_file():
    """打开文件选择对话框"""
    file_path = filedialog.askopenfilename()
    input_file_entry.delete(0, tk.END)
    input_file_entry.insert(0, file_path)

def browse_output_dir():
    """打开文件夹选择对话框"""
    dir_path = filedialog.askdirectory()
    output_dir_entry.delete(0, tk.END)
    output_dir_entry.insert(0, dir_path)

def open_settings():
    """打开设置窗口"""
    def save_settings():
        default_unit = default_unit_var.get()
        checksum_enable = checksum_enable_var.get()
        checksum_type = checksum_type_var.get()
        settings = {
            "default_unit": default_unit,
            "checksum_enable": checksum_enable,
            "checksum_type": checksum_type
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f)
            messagebox.showinfo("提示", "设置已保存")
            settings_window.destroy()
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")

    settings_window = tk.Toplevel(root)
    settings_window.title("设置")

    default_unit_label = tk.Label(settings_window, text="默认分割大小单位：")
    default_unit_label.pack(pady=5)

    default_unit_var = tk.StringVar(value=get_settings()["default_unit"])
    unit_options = ["B", "KB", "MB", "GB"]
    default_unit_menu = tk.OptionMenu(settings_window, default_unit_var, *unit_options)
    default_unit_menu.pack(pady=5)

    checksum_enable_label = tk.Label(settings_window, text="是否输出校验值：")
    checksum_enable_label.pack(pady=5)

    checksum_enable_var = tk.BooleanVar(value=get_settings().get("checksum_enable", False))
    checksum_enable_checkbox = tk.Checkbutton(settings_window, text="启用", variable=checksum_enable_var)
    checksum_enable_checkbox.pack(pady=5)

    checksum_type_label = tk.Label(settings_window, text="校验值类型：")
    checksum_type_label.pack(pady=5)

    checksum_type_var = tk.StringVar(value=get_settings().get("checksum_type", ""))
    checksum_type_options = ["SHA256", "MD5"]
    checksum_type_menu = tk.OptionMenu(settings_window, checksum_type_var, *checksum_type_options)
    checksum_type_menu.pack(pady=5)

    save_button = tk.Button(settings_window, text="保存", command=save_settings)
    save_button.pack(pady=5)

def get_settings():
    """从文件加载设置"""
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)
    except FileNotFoundError:
        # 如果设置文件不存在，则使用默认设置
        settings = {"default_unit": "B", "checksum_enable": False, "checksum_type": ""}
    return settings

# 创建主窗口
root = tk.Tk()
root.title("文件分割器")

# 输入框
input_file_label = tk.Label(root, text="输入文件：")
input_file_label.grid(row=0, column=0, padx=5, pady=5)
input_file_entry = tk.Entry(root)
input_file_entry.grid(row=0, column=1, padx=5, pady=5)

# 浏览按钮
browse_input_button = tk.Button(root, text="浏览", command=browse_input_file)
browse_input_button.grid(row=0, column=2, padx=5, pady=5)

# 输出目录
output_dir_label = tk.Label(root, text="输出目录：")
output_dir_label.grid(row=1, column=0, padx=5, pady=5)
output_dir_entry = tk.Entry(root)
output_dir_entry.grid(row=1, column=1, padx=5, pady=5)

# 浏览按钮
browse_output_button = tk.Button(root, text="浏览", command=browse_output_dir)
browse_output_button.grid(row=1, column=2, padx=5, pady=5)

# 输出文件名前缀
output_prefix_label = tk.Label(root, text="输出文件名前缀：")
output_prefix_label.grid(row=2, column=0, padx=5, pady=5)
output_prefix_entry = tk.Entry(root)
output_prefix_entry.grid(row=2, column=1, padx=5, pady=5)

# 分割大小
chunk_size_label = tk.Label(root, text="分割大小：")
chunk_size_label.grid(row=3, column=0, padx=5, pady=5)
chunk_size_entry = tk.Entry(root)
chunk_size_entry.grid(row=3, column=1, padx=5, pady=5)

# 单位选择框
unit_var = tk.StringVar(value=get_settings()["default_unit"])
unit_options = ["B", "KB", "MB", "GB"]
unit_menu = tk.OptionMenu(root, unit_var, *unit_options)
unit_menu.grid(row=3, column=2, padx=5, pady=5)

# 扩展名
extension_label = tk.Label(root, text="扩展名（可选）：")
extension_label.grid(row=4, column=0, padx=5, pady=5)
extension_entry = tk.Entry(root)
extension_entry.grid(row=4, column=1, padx=5, pady=5)

# 按钮
split_button = tk.Button(root, text="分割文件", command=split_file)
split_button.grid(row=5, column=0, columnspan=3, padx=5, pady=10)

# 设置按钮
settings_button = tk.Button(root, text="设置", command=open_settings)
settings_button.grid(row=6, column=0, columnspan=3, padx=5, pady=5)

# 错误提示
error_label = tk.Label(root, text="", fg="red")
error_label.grid(row=7, column=0, columnspan=3, padx=5, pady=5)

# 运行 GUI 或命令行模式
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="分割文件")
    parser.add_argument("-gui", action="store_true", help="启动 GUI 界面")
    args = parser.parse_args()

    # 检查是否传入 -gui 参数，或者没有传入任何参数
    if args.gui or len(sys.argv) == 1:
        # 启动 GUI
        root.mainloop()
    else:
        # 使用命令行参数运行脚本
        # 调用 split_file 函数，并将命令行参数传入
        split_file(args.input_file, args.output_prefix, args.chunk_size, args.output_dir, args.unit) 
