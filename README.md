
# HomDGCat Wiki's Mirror

---

一个玉衡杯本地镜像，仅包含中文版本 仅个人学习使用

---

## 文件结构

```
homdgcatwiki/
├── server.bat              # Start HTTP server
├── server.py               # HTTP server
├── index.html              
├── gi/                     # Genshin Impact part
│   ├── CH/Avatar/          # data for characters
│   ├── CH/Relic/           # data for relics
│   ├── gcg/                # data for GCG cards
│   │   ├── index.html      # GCG browser entry
│   ├── 3boss/              # data for 3BOSS
│   └── ...
├── sr/                     # Star Rail part
│   ├── data/CH/            # data
│   └── ...
├── about/                  # about page
├── javascripts/            # JS scripts
│   ├── gcg.js              # GCG core logic
│   ├── char.js             # character page logic
│   ├── home.js             # home logic
│   ├── spine_char.js       # Spine animation component for characters
│   └── ...
├── stylesheets/            # CSS styles
├── plugins/                # third-party libraries (jQuery)
├── images/                 # image resources (gitignore)
├── spine/                  # Spine animation resources (gitignore)
└── fonts/                  # font files
```

---