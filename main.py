"""
سامانه پایش هوشمند علائم تجاری سازمان ثبت اسناد و املاک کشور (SSAA)
نقطه ورود و اجرای برنامه
"""
import sys
import os

# اطمینان از قرارگیری مسیر ریشه پروژه در PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from gui.app import run_app

def main():
    print("==================================================")
    print("  سامانه پایش هوشمند علائم تجاری (مرکز مالکیت معنوی) ")
    print("  Iranian Intellectual Property Trademark Monitor   ")
    print("==================================================")
    run_app()

if __name__ == '__main__':
    main()
