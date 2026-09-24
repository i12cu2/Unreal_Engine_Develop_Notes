# UEAssetsToolkit

用于整理 Unreal Engine / Unity 素材包与工程文件的 Python 脚本集。

环境：Python 3.8+，删除到回收站需 `pip install send2trash`。  
所有移动/删除脚本默认 `DRY_RUN = True`，先预览日志，确认后改为 `False` 执行。

## 脚本列表

| 脚本                               | 功能                                                                                                                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `UEAssetsAnimationFilter.py`       | 深度查找单位内是否存在 `Animation` / `Animations` 文件夹，命中则移动整个单位到目标目录。                                                                                      |
| `UEAssetsClassify.py`              | 按 `.uproject` / `.uplugin` 将单位分类为项目工程、插件、素材，并移动到对应目录。                                                                                              |
| `UEAssetsCleanup.py`               | 深度删除指定文件夹（如“库文件”）和文件（如 `Read Me !.txt`、`manifest`），再回收空目录。                                                                                      |
| `UEAssetsContentExtract.py`        | 在单位内识别“类 Content 文件夹”（含 `__ExternalActors__`、`__ExternalObjects__`、`Collections`、`Developers` 任一子目录），若排除后有效子文件夹恰好一个，则提取并回收原单位。 |
| `UEAssetsExeFilter.py`             | 深度查找 `.exe`，命中则移动整个单位到 exe 目录。                                                                                                                              |
| `UEAssetsFolderList.py`            | 读取源目录下所有一级子文件夹名，逐行写入指定 txt 文件；只读源目录，不改动任何内容。                                                                                           |
| `UEAssetsFxFilter.py`              | 单位名包含 `fx` / `vfx`（不区分大小写）时，移动整个单位。                                                                                                                     |
| `UEAssetsFxFolderFilter.py`        | 单位内部存在恰好名为 `fx` / `vfx`（不区分大小写）的文件夹时，移动整个单位。                                                                                                   |
| `UEAssetsHarvest.py`               | 剥离单位的多层空壳嵌套，沿单链下钻，收割真正的内容根文件夹并回收原单位。                                                                                                      |
| `UEAssetsProjectContentExtract.py` | 在项目单位中定位 `.uproject` 同级的 `Content`，若排除名单后仅剩一个有效子文件夹，则提取该文件夹并回收原单位。                                                                 |
| `UEAssetsProjectNormalize.py`      | 找到 `.uproject`，将其父文件夹按 `.uproject` 前缀重命名，移动到目标目录并回收原单位。                                                                                         |
| `UEAssetsProjectRename.py`         | 就地重命名项目单位：以 `.uproject` 前缀为名，冲突时追加 `_1`、`_2`。                                                                                                          |
| `UEAssetsProjectScanner.py`        | 只读扫描，列出所有含 `.uproject` 的单位及具体文件路径，不做任何修改。                                                                                                         |
| `UEAssetsUnityFilter.py`           | 深度查找 `.unitypackage`，命中则移动整个单位到 Unity 目录。                                                                                                                   |

## 说明

- 移动时目标同名自动追加 `_1`、`_2`，不覆盖。
- 删除使用 `send2trash`，可从回收站恢复。
- 名单类配置均在脚本顶部，可按需增删。