document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const dropdownList = document.getElementById('dropdown-list');
    const selectedNodesDiv = document.getElementById('selected-nodes');
    const searchResults = document.getElementById('search-results');
    const btnClear = document.getElementById('btn-clear');
    const toggleBtn = document.getElementById('toggle-btn');
    const searchContent = document.getElementById('search-content');
    
    const checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
    const checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
    let selectedNodes = new Set();
    
    // Toggle visibility
    toggleBtn.addEventListener('click', function() {
        if (searchContent.classList.contains('hidden')) {
            searchContent.classList.remove('hidden');
            toggleBtn.textContent = 'Hide';
        } else {
            searchContent.classList.add('hidden');
            toggleBtn.textContent = 'Show';
        }
    });
    
    // Filter dropdown based on search
    searchInput.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        checkboxItems.forEach(item => {
            const label = item.querySelector('label').textContent.toLowerCase();
            item.style.display = label.includes(filter) ? 'flex' : 'none';
        });
    });
    
    // Update selected nodes display
    function updateSelectedDisplay() {
        selectedNodesDiv.innerHTML = '';
        if (selectedNodes.size === 0) {
            selectedNodesDiv.innerHTML = '<div style="color: #95a5a6; font-size: 12px; padding: 5px;">No nodes selected</div>';
            return;
        }
        
        selectedNodes.forEach(nodeName => {
            const tag = document.createElement('span');
            tag.className = 'selected-tag';
            tag.textContent = nodeName;
            tag.onclick = () => {
                selectedNodes.delete(nodeName);
                // Uncheck the checkbox
                checkboxes.forEach(cb => {
                    if (cb.value === nodeName) cb.checked = false;
                });
                updateSelectedDisplay();
                highlightNodes();
            };
            selectedNodesDiv.appendChild(tag);
        });
    }
    
    // Highlight selected nodes
    function highlightNodes() {
        if (selectedNodes.size === 0) {
            network.selectNodes([]);
            searchResults.textContent = '';
            return;
        }
        
        // Find matching node IDs
        const allNodes = network.body.data.nodes.get();
        const matchingIds = [];
        
        selectedNodes.forEach(nodeName => {
            const matches = allNodes.filter(node => 
                node.label === nodeName || 
                node.id === nodeName || 
                node.id === 'LET_' + nodeName
            );
            matches.forEach(m => matchingIds.push(m.id));
        });
        
        if (matchingIds.length > 0) {
            network.selectNodes(matchingIds);
            
            searchResults.textContent = `Highlighted ${matchingIds.length} node${matchingIds.length > 1 ? 's' : ''}`;
            searchResults.style.color = '#27ae60';
        } else {
            searchResults.textContent = 'No matching nodes found';
            searchResults.style.color = '#e74c3c';
        }
    }
    
    // Handle checkbox changes
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                selectedNodes.add(this.value);
            } else {
                selectedNodes.delete(this.value);
            }
            updateSelectedDisplay();
            highlightNodes();
        });
    });
    
    // Make clicking on label/item also toggle checkbox
    checkboxItems.forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT') {
                const checkbox = this.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            }
        });
    });
    
    // Clear button
    btnClear.addEventListener('click', function() {
        selectedNodes.clear();
        checkboxes.forEach(cb => cb.checked = false);
        updateSelectedDisplay();
        network.selectNodes([]);
        searchResults.textContent = '';
        searchInput.value = '';
        checkboxItems.forEach(item => item.style.display = 'flex');
    });
    
    // Initialize display
    updateSelectedDisplay();
});
