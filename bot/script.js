  document.addEventListener('DOMContentLoaded', () => {
        const tableBody = document.querySelector('#data-table tbody');
        const addForm = document.querySelector('#add-form');
        const selectAllCheckbox = document.querySelector('#select-all');
        const deleteSelectedButton = document.querySelector('#delete-selected');
        const messageContainer = document.querySelector('#message-container');
        const loadingIndicator = document.querySelector('.loading-indicator');
         const toggleAddFormButton = document.querySelector("#toggle-add-form");
           const formSection = document.querySelector(".form-section");
           let isFormExpanded = false;
           const connectionStatus = document.querySelector('#connection-status');
           const connectionIndicator = document.querySelector('#connection-indicator');
           const connectionText = document.querySelector('#connection-text');


       
        // 页面加载时移除 `collapsed` 类
        formSection.classList.remove('collapsed');


        // Function to show message
        const showMessage = (message, type) => {
          messageContainer.textContent = message;
          messageContainer.className = `message-container ${type}`;
           setTimeout(() => {
             messageContainer.textContent = '';
              messageContainer.className = 'message-container';
          }, 3000)
        };
          // Function to update connection status
        const updateConnectionStatus = (isConnected) => {
             if (isConnected) {
                  connectionIndicator.classList.remove('disconnected');
                 connectionIndicator.classList.add('connected');
                  connectionText.textContent = 'Connected';
            } else {
                  connectionIndicator.classList.remove('connected');
                 connectionIndicator.classList.add('disconnected');
                 connectionText.textContent = 'Disconnected';
              }
        };


        // Function to fetch and render data
         const fetchData = async () => {
             loadingIndicator.style.display = 'inline-block';
            try {
                const response = await fetch('/players');
                const data = await response.json();
                 renderTable(data);
                loadingIndicator.style.display = 'none';
                 updateConnectionStatus(true);
             } catch (error) {
                 console.error('Error fetching data:', error);
                 tableBody.innerHTML = '<tr><td colspan="4">Error loading data.</td></tr>';
                  loadingIndicator.style.display = 'none';
                 showMessage("Error loading data", 'error')
                  updateConnectionStatus(false);
             }
         };
          // 初始连接状态
         updateConnectionStatus(true);
        const renderTable = (data) => {
            tableBody.innerHTML = '';
            data.forEach((player) => {
                const row = document.createElement('tr');
                  row.innerHTML = `
                     <td>
                          <input type="checkbox" class="player-checkbox" value="${player.id}">
                    </td>
                    <td>${player.original_name}</td>
                    <td>${player.id}</td>
                    <td class='action-buttons'>
                       <button class="btn btn-danger" onclick="deletePlayer('${player.id}')">Delete</button>
                        <button class="btn btn-primary" onclick="editPlayer('${player.id}')">Edit</button>
                    </td>
                `;
                tableBody.appendChild(row);
              });

            updateDeleteButtonVisibility();
        }


        // 全选/取消全选功能
        selectAllCheckbox.addEventListener('change', () => {
            const checkboxes = document.querySelectorAll('.player-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = selectAllCheckbox.checked;
            });
           updateDeleteButtonVisibility();

        });

        // 监听复选框改变事件，更新删除按钮状态
         tableBody.addEventListener('change', event => {
             if(event.target.classList.contains('player-checkbox')) {
                 updateDeleteButtonVisibility()
             }
         })

        const updateDeleteButtonVisibility = () => {
            const checkedCheckboxes = document.querySelectorAll('.player-checkbox:checked');
            if(checkedCheckboxes.length > 0) {
                 deleteSelectedButton.style.display = 'inline-block';
            } else {
                deleteSelectedButton.style.display = 'none';
            }
        }

           // Function to delete selected players
         deleteSelectedButton.addEventListener('click', async () => {
           const checkedCheckboxes = document.querySelectorAll('.player-checkbox:checked');
            const idsToDelete = Array.from(checkedCheckboxes).map(checkbox => checkbox.value);

            if(idsToDelete.length > 0) {
               if (confirm("Are you sure you want to delete selected players?")) {
                    deleteSelectedButton.disabled = true;
                    showMessage("Deleting selected players...", "info")
                  try {
                      await Promise.all(idsToDelete.map(id =>  fetch(`/players/${id}`, { method: 'DELETE' })));
                        showMessage('Players deleted successfully', 'success');
                        fetchData();
                     } catch (error) {
                         console.error('Error deleting players:', error);
                           showMessage('Failed to delete selected players', 'error');
                           updateConnectionStatus(false);
                     } finally {
                         deleteSelectedButton.disabled = false;
                     }
               }
            } else {
                 showMessage('Please select players to delete', 'error');
           }
        });

         // Function to delete a player
        window.deletePlayer = async (id) => {
             if (confirm("Are you sure you want to delete this player?")) {
               try {
                     const response = await fetch(`/players/${id}`, { method: 'DELETE' });
                    showMessage("Deleting player...", "info")
                    if (response.ok) {
                        showMessage("Player deleted successfully", "success")
                        fetchData();
                     } else {
                         console.error('Error deleting player:', response.statusText);
                         showMessage('Failed to delete player', 'error');
                         updateConnectionStatus(false);
                    }
                } catch (error) {
                    console.error('Error deleting player:', error);
                    showMessage('Failed to delete player', 'error');
                     updateConnectionStatus(false);
                }
           }
       };

        // Function to handle edit player
        window.editPlayer = async (id) => {
            const editPlayer = await fetch(`/players/${id}`);
            if (!editPlayer.ok) {
                showMessage('Failed to edit player', 'error');
                  updateConnectionStatus(false);
                return
            }
            showMessage("Loading player...", "info");
            const player = await editPlayer.json()
           showMessage("", "info")

            // prompt dialog
            const originalName = prompt('Enter the new name', player.original_name);
            if (originalName === null) {
                return // User cancelled
            }

            const updatedPlayer = { ...player, original_name: originalName}

             try {
                 showMessage("Updating player...", "info")
                    const response = await fetch(`/players/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updatedPlayer)
                    });

                    if(response.ok) {
                         showMessage("Player updated successfully", "success");
                       fetchData();
                         updateConnectionStatus(true);
                    } else {
                        console.error('Error updating player:', response.statusText);
                        showMessage('Failed to update player', 'error');
                         updateConnectionStatus(false);
                   }
                } catch (error) {
                    console.error('Error updating player:', error);
                    showMessage('Failed to update player', 'error');
                    updateConnectionStatus(false);
                 }
        };

        // Function to handle add player form submission
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const original_name = document.querySelector('#original_name').value;
            const id = document.querySelector('#id').value;
              if(!original_name || !id) {
                   showMessage("Please fill in all fields","error")
                   return;
             }

            try {
                 showMessage("Adding player...", "info");
                  addForm.querySelector('button').disabled = true;
                const response = await fetch('/players', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({original_name, id }),
               });
                if(response.ok) {
                      addForm.reset();
                        showMessage("Player added successfully", "success");
                      fetchData();
                       updateConnectionStatus(true);
                } else {
                     console.error('Error adding player:', response.statusText);
                      showMessage('Failed to add player', 'error');
                       updateConnectionStatus(false);
                 }
            } catch (error) {
                console.error('Error adding player:', error);
                showMessage('Failed to add player', 'error');
                 updateConnectionStatus(false);
            } finally {
                 addForm.querySelector('button').disabled = false;
           }
        });

        fetchData();

          toggleAddFormButton.addEventListener('click', () => {
            formSection.classList.toggle('expanded')
            isFormExpanded = !isFormExpanded;
              if(isFormExpanded) {
                  toggleAddFormButton.textContent = 'Close Add Player'
              } else {
                 toggleAddFormButton.textContent = 'Add New Player'
              }
         });

         // 定时检查服务器连接状态
         setInterval(async () => {
             try {
               await fetch('/players');
               updateConnectionStatus(true);
            } catch (error) {
                 updateConnectionStatus(false);
            }
         }, 5000);

    });