Il2CppDumper.exe "C:\Users\Benson\Desktop\BlueArchive-Hack\GameAssembly.dll" "C:\Users\Benson\Desktop\BlueArchive-Hack\BlueArchive_Data\il2cpp_data\Metadata\global-metadata.dat" .\output
pause
Cpp2IL.exe --game-path "C:\Users\Benson\Desktop\BlueArchive-Hack" --exe-name BlueArchive --output-as diffable-cs
pause
Cpp2IL.exe --game-path "C:\Users\Benson\Desktop\BlueArchive-Hack" --exe-name BlueArchive --output-as dll_default
pause