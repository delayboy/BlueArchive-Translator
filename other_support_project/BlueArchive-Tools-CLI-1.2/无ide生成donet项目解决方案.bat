dotnet new sln -n BlueArchiveTools
dotnet sln add BlueArchiveTools.CLI/BlueArchiveTools.CLI.csproj
dotnet sln add cn_metadata_exporter/cn_metadata_exporter.csproj
dotnet sln add UABEA/UABEAvalonia/UABEAvalonia.csproj
dotnet sln add Il2CppInspectorRedux/Il2CppInspector.CLI/Il2CppInspector.CLI.csproj
dotnet build -c Debug
pause