 const express = require('express');
    const path = require('path');
    const fs = require('fs');
    const app = express();
    const port = 3000;

    const playerDataFile = '../player.json';

   let jsonData = JSON.parse(fs.readFileSync(playerDataFile, 'utf8'));

    // 监听 player.json 文件变化
     fs.watchFile(playerDataFile, (curr, prev) => {
           console.log("Player.json file changed, reloading data...");
           jsonData = JSON.parse(fs.readFileSync(playerDataFile, 'utf8')); // reload data
      });
    app.use(express.json());
    app.use(express.static(path.join(__dirname)));

   // 处理访问 `/` 的请求，返回 index.html 文件
    app.get('/', (req, res) => {
      res.sendFile(path.join(__dirname, 'index.html'));
    });
    
      // 其他路由代码 ( /players,  /players/:id 等) ...
      
       app.get('/players', (req, res) => {
        res.json(jsonData);
      });

      app.get('/players/:id', (req, res) => {
        const id = req.params.id;
        const player = jsonData.find(p => p.id === id);
        if (player) {
          res.json(player);
        } else {
          res.status(404).send('Player not found');
        }
      });

      app.post('/players', (req, res) => {
        const newPlayer = req.body;
        jsonData.push(newPlayer);
        fs.writeFileSync(playerDataFile, JSON.stringify(jsonData, null, 2), 'utf8');
        res.status(201).send('Player added successfully');
      });

      app.put('/players/:id', (req, res) => {
        const id = req.params.id;
        const updatedPlayer = req.body;
        const playerIndex = jsonData.findIndex(p => p.id === id);
        if (playerIndex !== -1) {
          jsonData[playerIndex] = updatedPlayer;
          fs.writeFileSync(playerDataFile, JSON.stringify(jsonData, null, 2), 'utf8');
          res.send('Player updated successfully');
        } else {
          res.status(404).send('Player not found');
        }
      });

      app.delete('/players/:id', (req, res) => {
        const id = req.params.id;
        const playerIndex = jsonData.findIndex(p => p.id === id);
        if (playerIndex !== -1) {
          jsonData.splice(playerIndex, 1);
          fs.writeFileSync(playerDataFile, JSON.stringify(jsonData, null, 2), 'utf8');
          res.send('Player deleted successfully');
        } else {
          res.status(404).send('Player not found');
        }
      });



      app.listen(port, '0.0.0.0',() => {
        console.log(`Server listening at http://0.0.0.0:${port}`);
      });