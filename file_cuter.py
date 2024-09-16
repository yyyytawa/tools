import tkinter as tk
from tkinter import filedialog
import os
import argparse
import sys

def split_file():
    input_file = input_file_entry.get()
    output_dir = output_dir_entry.get()
    output_prefix = output_prefix_entry.get()
    chunk_size_str = chunk_size_entry.get()
    unit = unit_var.get()

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
            if unit == "KB":
                chunk_size *= 1024
            elif unit == "MB":
                chunk_size *= 1024 * 1024
            elif unit == "GB":
                chunk_size *= 1024 * 1024 * 1024

            while True:
                chunk = f_in.read(chunk_size)
                if not chunk:
                    break
                output_file = os.path.join(output_dir, f"{output_prefix}_{chunk_num:03d}")
                with open(output_file, "wb") as f_out:
                    f_out.write(chunk)
                chunk_num += 1
                print(f"已分割 {output_file} (大小: {len(chunk)} 字节)")
            print(f"文件 {input_file} 已成功分割成 {chunk_num} 个文件。")
            error_label.config(text=f"文件已成功分割成 {chunk_num} 个文件。")
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
unit_var = tk.StringVar(value="B")
unit_options = ["B", "KB", "MB", "GB"]
unit_menu = tk.OptionMenu(root, unit_var, *unit_options)
unit_menu.grid(row=3, column=2, padx=5, pady=5)

# 按钮
split_button = tk.Button(root, text="分割文件", command=split_file)
split_button.grid(row=4, column=0, columnspan=3, padx=5, pady=10)

# 错误提示
error_label = tk.Label(root, text="", fg="red")
error_label.grid(row=5, column=0, columnspan=3, padx=5, pady=5)

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
        parser = argparse.ArgumentParser(description="分割文件")
        parser.add_argument("input_file", help="要分割的文件路径")
        parser.add_argument("output_prefix", help="输出文件名前缀")
        parser.add_argument("chunk_size", type=int, help="每个分割文件的字节大小")
        parser.add_argument("-o", "--output_dir", default=None, help="输出目录")
        parser.add_argument("-u", "--unit", default="B", choices=["B", "KB", "MB", "GB"], help="分割大小单位")
        args = parser.parse_args()

        split_file(args.input_file, args.output_prefix, args.chunk_size, args.output_dir, args.unit)
