/**
 * Graph filtering and visibility management
 */

const GraphFilters = (function() {
    function getSelectedEdgeDirection(edgeDirectionRadios) {
        let direction = 'both';
        edgeDirectionRadios.forEach(radio => {
            if (radio.checked) direction = radio.value;
        });
        return direction;
    }

    function getSelectedFilterMode(filterModeRadios) {
        let mode = 'include';
        filterModeRadios.forEach(radio => {
            if (radio.checked) mode = radio.value;
        });
        return mode;
    }

    function shouldIncludeEdge(edge, matchingIds, edgeDirection, isEdgeHiddenByTypeFilter) {
        if (isEdgeHiddenByTypeFilter(edge)) return false;
        
        const isOutgoing = matchingIds.has(edge.from);
        const isIncoming = matchingIds.has(edge.to);
        
        if (edgeDirection === 'both') return isOutgoing || isIncoming;
        if (edgeDirection === 'outgoing') return isOutgoing;
        if (edgeDirection === 'incoming') return isIncoming;
        
        return false;
    }

    function buildNeighborhoodFromEdges(network, matchingIds, edgeDirection, isEdgeHiddenByTypeFilter) {
        const allEdges = network.body.data.edges.get();
        const connectedNodeIds = new Set(matchingIds);
        
        allEdges.forEach(edge => {
            if (!shouldIncludeEdge(edge, matchingIds, edgeDirection, isEdgeHiddenByTypeFilter)) return;
            
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            
            if (isOutgoing) connectedNodeIds.add(edge.to);
            if (isIncoming) connectedNodeIds.add(edge.from);
        });
        
        return connectedNodeIds;
    }

    function applyExcludeMode(network, matchingIds, isEdgeHiddenByTypeFilter, showIsolatedNodes) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
        // Identify truly isolated nodes (nodes with no edges at all)
        const nodesWithAnyEdges = new Set();
        allEdges.forEach(edge => {
            nodesWithAnyEdges.add(edge.from);
            nodesWithAnyEdges.add(edge.to);
        });
        
        // Hide edges connected to excluded nodes
        const updatedEdges = allEdges.map(edge => {
            const hiddenByTypeFilter = isEdgeHiddenByTypeFilter(edge);
            const connectedToExcluded = matchingIds.has(edge.from) || matchingIds.has(edge.to);
            const hidden = hiddenByTypeFilter || connectedToExcluded;
            return { ...edge, hidden: hidden, physics: !hidden };
        });
        
        // Collect nodes with visible edges
        const nodesWithVisibleEdges = new Set();
        updatedEdges.forEach(edge => {
            if (!edge.hidden) {
                nodesWithVisibleEdges.add(edge.from);
                nodesWithVisibleEdges.add(edge.to);
            }
        });
        
        // Hide excluded nodes; for other nodes, show if they have visible edges OR are isolated (with checkbox checked)
        const updatedNodes = allNodes.map(node => {
            const isExcluded = matchingIds.has(node.id);
            if (isExcluded) {
                return { ...node, hidden: true };
            }
            
            const isIsolated = !nodesWithAnyEdges.has(node.id);
            const hasVisibleEdges = nodesWithVisibleEdges.has(node.id);
            
            // Show node if: has visible edges OR (is isolated AND showIsolatedNodes is checked)
            const shouldShow = hasVisibleEdges || (isIsolated && showIsolatedNodes);
            return { ...node, hidden: !shouldShow };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.body.data.edges.update(updatedEdges);
        network.selectNodes([]);
        
        const visibleCount = allNodes.filter(node => {
            const isExcluded = matchingIds.has(node.id);
            const isIsolated = !nodesWithAnyEdges.has(node.id);
            const hasVisibleEdges = nodesWithVisibleEdges.has(node.id);
            return !isExcluded && (hasVisibleEdges || (isIsolated && showIsolatedNodes));
        }).length;
        
        return {
            excludedCount: matchingIds.size,
            visibleCount: visibleCount
        };
    }

    function applyIncludeMode(network, matchingIds, connectedNodeIds, edgeDirection, isEdgeHiddenByTypeFilter) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
        // Update edge visibility
        const updatedEdges = allEdges.map(edge => {
            if (isEdgeHiddenByTypeFilter(edge)) {
                return { ...edge, hidden: true, physics: false };
            }
            
            if (!shouldIncludeEdge(edge, matchingIds, edgeDirection, isEdgeHiddenByTypeFilter)) {
                return { ...edge, hidden: true, physics: false };
            }
            
            const isOutgoing = matchingIds.has(edge.from);
            const isIncoming = matchingIds.has(edge.to);
            const edgeVisible = isOutgoing || isIncoming;
            
            return { ...edge, hidden: !edgeVisible, physics: edgeVisible };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility
        const updatedNodes = allNodes.map(node => {
            return { ...node, hidden: !connectedNodeIds.has(node.id) };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.selectNodes(Array.from(matchingIds));
        
        return {
            selectedCount: matchingIds.size,
            neighborCount: connectedNodeIds.size - matchingIds.size
        };
    }

    function applyCommonEdgesMode(network, matchingIds, isEdgeHiddenByTypeFilter) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
        let commonEdgeCount = 0;
        
        // Update edge visibility - only show edges where BOTH endpoints are in selected nodes
        const updatedEdges = allEdges.map(edge => {
            if (isEdgeHiddenByTypeFilter(edge)) {
                return { ...edge, hidden: true, physics: false };
            }
            
            const fromSelected = matchingIds.has(edge.from);
            const toSelected = matchingIds.has(edge.to);
            const edgeVisible = fromSelected && toSelected;
            
            if (edgeVisible) {
                commonEdgeCount++;
            }
            
            return { ...edge, hidden: !edgeVisible, physics: edgeVisible };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility - only show selected nodes
        const updatedNodes = allNodes.map(node => {
            return { ...node, hidden: !matchingIds.has(node.id) };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.selectNodes(Array.from(matchingIds));
        
        return {
            selectedCount: matchingIds.size,
            neighborCount: 0,
            commonEdgeCount: commonEdgeCount
        };
    }

    function updateEdgeVisibility(network, selectedNodes, isEdgeHiddenByTypeFilter, highlightNodes, showIsolatedNodes) {
        const edges = network.body.data.edges.get();
        const nodes = network.body.data.nodes.get();
        const connectedNodes = new Set();
        
        // Identify nodes with any edges (visible or hidden)
        const nodesWithAnyEdges = new Set();
        edges.forEach(edge => {
            nodesWithAnyEdges.add(edge.from);
            nodesWithAnyEdges.add(edge.to);
        });
        
        // Update edges and track connected nodes
        const updatedEdges = edges.map(edge => {
            const hidden = isEdgeHiddenByTypeFilter(edge);
            
            if (!hidden) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
            
            return { ...edge, hidden: hidden, physics: !hidden };
        });
        
        network.body.data.edges.update(updatedEdges);
        
        // Update node visibility
        if (selectedNodes.size > 0) {
            highlightNodes(); // Handles node visibility with selection
        } else {
            const updatedNodes = nodes.map(node => {
                const isConnected = connectedNodes.has(node.id);
                const isIsolated = !nodesWithAnyEdges.has(node.id);
                // Show node if: has visible edges OR (is isolated AND showIsolatedNodes is true)
                return { ...node, hidden: !isConnected && !(isIsolated && showIsolatedNodes) };
            });
            network.body.data.nodes.update(updatedNodes);
            GraphSCC.refreshSccs(network, sccs);
        }
        
        return connectedNodes;
    }
    
    function setupFilterModeHandlers(filterModeRadios, selectedNodes, selectedPartitions, updateFilterModeCallback, highlightCallback) {
        filterModeRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                updateFilterModeCallback();
                if (selectedNodes.size > 0 || selectedPartitions.size > 0) highlightCallback();
            });
        });
    }

    return {
        getSelectedEdgeDirection,
        getSelectedFilterMode,
        shouldIncludeEdge,
        buildNeighborhoodFromEdges,
        applyExcludeMode,
        applyIncludeMode,
        applyCommonEdgesMode,
        updateEdgeVisibility,
        setupFilterModeHandlers
    };
})();
