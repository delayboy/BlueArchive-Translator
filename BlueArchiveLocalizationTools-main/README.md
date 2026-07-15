# Blue Archive Localization Tools
This project provides the tools necessary to create localization resources for Blue Archive.

此项目载有创建蔚蓝档案本地化资源所需工具。

## Disclaimer / 免责声明
This project is intended solely for educational and demonstrative purposes and does not provide any actual resources. Please note that all content downloaded through this project should only be used for legal and legitimate purposes. The developers are not liable for any direct or indirect loss, damage, legal liability, or other consequences that may arise from the use of this project. Users assume all risks associated with the use of this project and must ensure compliance with all relevant laws and regulations. If anyone uses this project for any unauthorized or illegal activities, the developers bear no responsibility. Users are responsible for their own actions and should understand the risks involved in using this project. 

"Blue Archive" is a registered trademark of NEXON Korea Corp. & NEXON GAMES Co., Ltd. All rights reserved.

该仓库仅供学习和展示用途，不托管任何实际资源。请注意，所有通过本项目下载的内容均应仅用于合法和正当的目的。开发者不对任何人因使用本项目而可能引发的直接或间接的损失、损害、法律责任或其他后果承担任何责任。用户在使用本项目时需自行承担风险，并确保遵守所有相关法律法规。如果有人使用本项目从事任何未经授权或非法的活动，开发者对此不承担任何责任。用户应对自身的行为负责，并了解使用本项目可能带来的任何风险。 

“蔚蓝档案”是上海星啸网络科技有限公司的注册商标，版权所有。 

「ブルーアーカイブ」は株式会社Yostarの登録商標です。著作権はすべて保有されています。 

## Usage
This repository can be used for unpacking and repacking most excels for all three servers (jp, gl, cn) if provided with dumpable game executables OR static C# dumps in which types are parsed correctly, to be used to generate FlatData.

This repository does not provide direct FlatData nor any of the aforementioned items, but you can see setup_flatdata for reference in acquiring dumps (intended to be used for jp only).

Additionally, this repository also provides code necessary for packing and unpacking voice zips. This does not go into the nuance of Criware formats, and does not provide methods to unpack those (which means this does not apply to some cn voice lines).

This repository does not go into the nuance of crc manipulation, catalog manipulation, and other changes necessary fir production.
For usage in production, see [asfu222/BACNLocalizationResources](https://github.com/asfu222/BACNLocalizationResources)

For asset bundles, see [asfu222/commonpngsrc](https://github.com/asfu222/commonpngsrc)
