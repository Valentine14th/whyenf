document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search-input');
    const dropdownList = document.getElementById('dropdown-list');
    const selectedNodesDiv = document.getElementById('selected-nodes');
    const searchResults = document.getElementById('search-results');
    const btnClear = document.getElementById('btn-clear');
    const toggleBtn = document.getElementById('toggle-btn');
    const searchContent = document.getElementById('search-content');
    const letEdgesCheckbox = document.getElementById('show-let-edges');
    const implicationEdgesCheckbox = document.getElementById('show-implication-edges');
    const cauByCauEdgesCheckbox = document.getElementById('show-caubycau-edges');
    const cauBySupEdgesCheckbox = document.getElementById('show-caubysup-edges');
    const showAllNeighborhoodEdgesCheckbox = document.getElementById('show-all-neighborhood-edges');
    const edgeDirectionRadios = document.getElementsByName('edge-direction');
    
    const checkboxItems = dropdownList.querySelectorAll('.checkbox-item');
    const checkboxes = dropdownList.querySelectorAll('input[type="checkbox"]');
    let selectedNodes = new Set();
    
    // Helper function to check if an edge should be hidden by type filters
    function isEdgeHiddenByTypeFilter(edge) {
        const showLetEdges = letEdgesCheckbox ? letEdgesCheckbox.checked : true;
        const showImplicationEdges = implicationEdgesCheckbox ? implicationEdgesCheckbox.checked : true;
        const showCauByCauEdges = cauByCauEdgesCheckbox ? cauByCauEdgesCheckbox.checked : true;
        const showCauBySupEdges = cauBySupEdgesCheckbox ? cauBySupEdgesCheckbox.checked : true;
        
        const edgeColor = edge.color && edge.color.color ? edge.color.color : edge.color;
        const isImplicationEdge = edge.dashes && edge.dashes.length > 0;
        const isCauByCauEdge = edgeColor === '#27ae60';
        const isCauBySupEdge = edgeColor === '#3498db';
        const isMixedCausalityEdge = edgeColor === '#9b59b6';
        const isLetEdge = !isImplicationEdge && !isCauByCauEdge && !isCauBySupEdge && !isMixedCausalityEdge;
        
        if (isLetEdge && !showLetEdges) return true;
        if (isImplicationEdge && !showImplicationEdges) return true;
        if (isCauByCauEdge && !showCauByCauEdges) return true;
        if (isCauBySupEdge && !showCauBySupEdges) return true;
        if (isMixedCausalityEdge && (!showCauByCauEdges || !showCauBySupEdges)) return true;
        
        return false;
    }
    
    // Clear all selections when network is ready
    network.once('stabilizationIterationsDone', function() {
        network.selectNodes([]);
        network.selectEdges([]);
        network.unselectAll();
    });
    
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
    
    // Filter edges based on checkboxes
    function updateEdgeVisibility() {
        const showLetEdges = letEdgesCheckbox ? letEdgesCheckbox.checked : true;
        const showImplicationEdges = implicationEdgesCheckbox ? implicationEdgesCheckbox.checked : true;
        const showCauByCauEdges = cauByCauEdgesCheckbox ? cauByCauEdgesCheckbox.checked : true;
        const showCauBySupEdges = cauBySupEdgesCheckbox ? cauBySupEdgesCheckbox.checked : true;
        
        const edges = network.body.data.edges.get();
        const nodes = network.body.data.nodes.get();
        
        // Track which nodes are connected to visible edges
        const connectedNodes = new Set();
        
        const updatedEdges = edges.map(edge => {
            let hidden = false;
            
            // Identify edge type by color
            const edgeColor = edge.color && edge.color.color ? edge.color.color : edge.color;
            const isImplicationEdge = edge.dashes && edge.dashes.length > 0; // Purple dashed edges
            const isCauByCauEdge = edgeColor === '#27ae60'; // Green edges
            const isCauBySupEdge = edgeColor === '#3498db'; // Blue edges
            const isMixedCausalityEdge = edgeColor === '#9b59b6'; // Purple edges
            const isLetEdge = !isImplicationEdge && !isCauByCauEdge && !isCauBySupEdge && !isMixedCausalityEdge;
            
            if (isLetEdge && !showLetEdges) {
                hidden = true;
            }
            if (isImplicationEdge && !showImplicationEdges) {
                hidden = true;
            }
            if (isCauByCauEdge && !showCauByCauEdges) {
                hidden = true;
            }
            if (isCauBySupEdge && !showCauBySupEdges) {
                hidden = true;
            }
            if (isMixedCausalityEdge && (!showCauByCauEdges || !showCauBySupEdges)) {
                hidden = true;
            }
            
            // Track connected nodes for visible edges
            if (!hidden) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
            
            // Disable physics for hidden edges so they don't affect layout
            return { ...edge, hidden: hidden, physics: !hidden };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // If nodes are already selected, update visibility with selection filter
        // Otherwise, just update based on edge connectivity
        if (selectedNodes.size > 0) {
            highlightNodes(); // This will handle node visibility with selection
        } else {
            // Update nodes visibility based on connection only
            const updatedNodes = nodes.map(node => {
                const isConnected = connectedNodes.has(node.id);
                return { ...node, hidden: !isConnected };
            });
            network.body.data.nodes.update(updatedNodes);
        }
        
        // Filter dropdown to show only visible nodes
        filterDropdownByVisibility(connectedNodes);
    }
    
    // Filter dropdown items based on visible nodes
    function filterDropdownByVisibility(connectedNodes) {
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        
        // Build set of visible node names
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                // Add the actual node name (strip LET_ prefix if present)
                if (node.id.startsWith('LET_')) {
                    visibleNodeNames.add(node.id.substring(4));
                } else {
                    visibleNodeNames.add(node.id);
                }
            }
        });
        
        // Filter dropdown items
        checkboxItems.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const nodeName = checkbox.value;
            
            // Apply both search filter and visibility filter
            const searchFilter = searchInput.value.toLowerCase();
            const label = item.querySelector('label').textContent.toLowerCase();
            const matchesSearch = label.includes(searchFilter);
            const isVisible = visibleNodeNames.has(nodeName);
            
            item.style.display = (matchesSearch && isVisible) ? 'flex' : 'none';
        });
    }

    
    // Edge visibility toggle handlers
    if (letEdgesCheckbox) letEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (implicationEdgesCheckbox) implicationEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (cauByCauEdgesCheckbox) cauByCauEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    if (cauBySupEdgesCheckbox) cauBySupEdgesCheckbox.addEventListener('change', updateEdgeVisibility);
    
    // Selection mode toggle handler
    if (showAllNeighborhoodEdgesCheckbox) {
        showAllNeighborhoodEdgesCheckbox.addEventListener('change', function() {
            if (selectedNodes.size > 0) {
                highlightNodes(); // Re-apply highlighting with new mode
            }
        });
    }
    
    // Edge direction radio handlers
    edgeDirectionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (selectedNodes.size > 0) {
                highlightNodes(); // Re-apply highlighting with new direction
            }
        });
    });
    
    // Filter dropdown based on search
    searchInput.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        
        // Get currently visible nodes based on edge toggles
        const showLetEdges = letEdgesCheckbox ? letEdgesCheckbox.checked : true;
        const showImplicationEdges = implicationEdgesCheckbox ? implicationEdgesCheckbox.checked : true;
        const showCauByCauEdges = cauByCauEdgesCheckbox ? cauByCauEdgesCheckbox.checked : true;
        const showCauBySupEdges = cauBySupEdgesCheckbox ? cauBySupEdgesCheckbox.checked : true;
        const edges = network.body.data.edges.get();
        const connectedNodes = new Set();
        
        edges.forEach(edge => {
            const edgeColor = edge.color && edge.color.color ? edge.color.color : edge.color;
            const isImplicationEdge = edge.dashes && edge.dashes.length > 0;
            const isCauByCauEdge = edgeColor === '#27ae60';
            const isCauBySupEdge = edgeColor === '#3498db';
            const isMixedCausalityEdge = edgeColor === '#9b59b6';
            const isLetEdge = !isImplicationEdge && !isCauByCauEdge && !isCauBySupEdge && !isMixedCausalityEdge;
            let hidden = false;
            
            if (isLetEdge && !showLetEdges) hidden = true;
            if (isImplicationEdge && !showImplicationEdges) hidden = true;
            if (isCauByCauEdge && !showCauByCauEdges) hidden = true;
            if (isCauBySupEdge && !showCauBySupEdges) hidden = true;
            if (isMixedCausalityEdge && (!showCauByCauEdges || !showCauBySupEdges)) hidden = true;
            
            if (!hidden) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
        });
        
        const allNodes = network.body.data.nodes.get();
        const visibleNodeNames = new Set();
        allNodes.forEach(node => {
            if (connectedNodes.has(node.id)) {
                if (node.id.startsWith('LET_')) {
                    visibleNodeNames.add(node.id.substring(4));
                } else {
                    visibleNodeNames.add(node.id);
                }
            }
        });
        
        checkboxItems.forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            const label = item.querySelector('label').textContent.toLowerCase();
            const isVisible = visibleNodeNames.has(checkbox.value);
            item.style.display = (label.includes(filter) && isVisible) ? 'flex' : 'none';
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
    
    // Highlight selected nodes and show only them with their neighbors
    function highlightNodes() {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
        if (selectedNodes.size === 0) {
            // Reset: show all nodes based on edge visibility
            network.selectNodes([]);
            searchResults.textContent = '';
            updateEdgeVisibility(); // This will restore proper visibility
            return;
        }
        
        // Find matching node IDs for selected nodes
        const matchingIds = new Set();
        
        selectedNodes.forEach(nodeName => {
            const matches = allNodes.filter(node => 
                node.label === nodeName || 
                node.id === nodeName || 
                node.id === 'LET_' + nodeName
            );
            matches.forEach(m => matchingIds.add(m.id));
        });
        
        if (matchingIds.size === 0) {
            searchResults.textContent = 'No matching nodes found';
            searchResults.style.color = '#e74c3c';
            return;
        }
        
        // Find all nodes connected to selected nodes (neighbors)
        const connectedNodeIds = new Set(matchingIds);
        const showAllEdges = showAllNeighborhoodEdgesCheckbox ? showAllNeighborhoodEdgesCheckbox.checked : false;
        
        // Get selected edge direction
        let edgeDirection = 'both';
        edgeDirectionRadios.forEach(radio => {
            if (radio.checked) edgeDirection = radio.value;
        });
        
        allEdges.forEach(edge => {
            // Skip edges hidden by type filter
            if (isEdgeHiddenByTypeFilter(edge)) return;
            
            // Check direction filter
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            
            let directionMatch = false;
            if (edgeDirection === 'both') {
                directionMatch = isOutgoing || isIncoming;
            } else if (edgeDirection === 'outgoing') {
                directionMatch = isOutgoing;
            } else if (edgeDirection === 'incoming') {
                directionMatch = isIncoming;
            }
            
            if (!directionMatch) return;
            
            // Add connected nodes to visible set
            if (isOutgoing) {
                connectedNodeIds.add(edge.to);
            }
            if (isIncoming) {
                connectedNodeIds.add(edge.from);
            }
        });
        
        // Update edge visibility based on mode
        const updatedEdges = allEdges.map(edge => {
            // Check if edge should be hidden by type filter
            const hiddenByTypeFilter = isEdgeHiddenByTypeFilter(edge);
            if (hiddenByTypeFilter) {
                return { ...edge, hidden: true, physics: false };
            }
            
            // Check direction filter
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            
            let directionMatch = false;
            if (edgeDirection === 'both') {
                directionMatch = isOutgoing || isIncoming;
            } else if (edgeDirection === 'outgoing') {
                directionMatch = isOutgoing;
            } else if (edgeDirection === 'incoming') {
                directionMatch = isIncoming;
            }
            
            if (!directionMatch) {
                return { ...edge, hidden: true, physics: false };
            }
            
            if (showAllEdges) {
                // Show all edges where both endpoints are in the visible neighborhood
                const edgeVisible = connectedNodeIds.has(edge.from) && connectedNodeIds.has(edge.to);
                return { ...edge, hidden: !edgeVisible, physics: edgeVisible };
            } else {
                // Show only edges directly connected to selected nodes
                const edgeVisible = isOutgoing || isIncoming;
                return { ...edge, hidden: !edgeVisible, physics: edgeVisible };
            }
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility: show only selected nodes and their neighbors
        const updatedNodes = allNodes.map(node => {
            return { ...node, hidden: !connectedNodeIds.has(node.id) };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.selectNodes(Array.from(matchingIds));
        
        searchResults.textContent = `Showing ${matchingIds.size} selected node${matchingIds.size > 1 ? 's' : ''} with ${connectedNodeIds.size - matchingIds.size} neighbor${connectedNodeIds.size - matchingIds.size !== 1 ? 's' : ''}`;
        searchResults.style.color = '#27ae60';
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
    
    // Clear all selections on page load
    selectedNodes.clear();
    checkboxes.forEach(cb => cb.checked = false);
    searchInput.value = '';
    searchResults.textContent = '';
    
    // Ensure all edge type toggles are checked on page load
    if (letEdgesCheckbox) letEdgesCheckbox.checked = true;
    if (implicationEdgesCheckbox) implicationEdgesCheckbox.checked = true;
    if (cauByCauEdgesCheckbox) cauByCauEdgesCheckbox.checked = true;
    if (cauBySupEdgesCheckbox) cauBySupEdgesCheckbox.checked = true;
    
    // Ensure "both" is selected for edge direction
    edgeDirectionRadios.forEach(radio => {
        if (radio.value === 'both') {
            radio.checked = true;
        }
    });
    
    // Initialize display
    updateSelectedDisplay();
});
