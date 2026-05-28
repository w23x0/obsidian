### 项目窗口目录
文件分类
.anim动画
	**Anim_UserEdit**: 预留自定义修改或添加的动画片段目录。
	**Anim_Animator**: 存放核心状态机动画、动作捕捉或基础循环动画的物理文件。
	**BlendTrees**: 存放混合树文件。用于根据浮点数参数（如移动速度、摇杆坐标）线性插值混合多个动画（例如：融合前/后/左/右走动动画）。
	**Controllers**: 存放动画控制器（`Animator Controller`）。底层是有限状态机（FSM），负责管理动画状态跳转逻辑、Layer 权重及 Avatar Mask。
**Expressiona (Expressions)**: 存放 VRChat 表情控制
**Icon**: 存放 2D 贴图（`.png` 或 `.tga`）环形菜单中显示的图标
**fbx**: 存放原始 3D 模型文件（`.fbx`）。包含网格数据（Mesh）、骨骼绑定信息（Skeleton/Joints）、顶点权重（Vertex Weights）以及默认的 Morph Target (BlendShape) 数据。
**material / material_2P**: 存放材质球文件（`.mat`）。材质球本质上是 Shader 的参数序列化配置文件（保存了 Shader 引用、贴图索引、颜色值及各类渲染标记）。`2P` 通常指代第二套配色（Player 2 Color / Alternate Skin）。
**Mobile**: 存放针对移动端
**Prefab**: 预制体文件（`.prefab`）已经绑定好材质和骨骼
**tex (Textures)**: 存放原始纹理贴图（`.png`、`.jpg` 或 `.tga`），包括反照率贴图（Albedo/Main Tex）、法线贴图（Normal Map）、遮罩贴图（Mask Map，用于控制卡通渲染的阴影、高光、描边范围）。

### 操作
F 快速聚焦
主摄像机 Ctrl + Shift + F保持
### 换衣
有些成品模不能解包