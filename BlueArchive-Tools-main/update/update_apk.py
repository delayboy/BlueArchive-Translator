import argparse
from utils.apktools import ApkTools

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update Blue Archive APK")
    parser.add_argument("--server", type=str, default="JP", help="服务器选择")
    parser.add_argument("--sdkurl", type=str, default="", help="修改SDK_Url")
    parser.add_argument("--gamemainconfig", type=str, default="", help="修改GameMainConfig")
    parser.add_argument("--coexist", type=str, default="", help="自定义包名")
    parser.add_argument("--modifylogin", type=str, default="", help="修改登录界面语言")
    parser.add_argument("--replace", action="store_true", help="替换资源")
    parser.add_argument("--modifybundle", action="store_true", help="修改bundle资源")
    parser.add_argument("--repo", type=str, default="BAJpApkSrc", help="资源文件夹路径")
    parser.add_argument("--trustcert", action="store_true", help="启用信任证书")
    args = parser.parse_args()

    apk_tools = ApkTools(repo=args.repo)
    apk_tools.main(
        coexist=args.coexist,
        sdkurl=args.sdkurl,
        gamemainconfig=args.gamemainconfig,
        trustcert=args.trustcert,
        modifylogin=args.modifylogin,
        replace=args.replace,
        modifybundle=args.modifybundle,
        server=args.server
    )
