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

    function applyExcludeMode(network, matchingIds, isEdgeHiddenByTypeFilter) {
        const allNodes = network.body.data.nodes.get();
        const allEdges = network.body.data.edges.get();
        
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
        
        // Hide excluded nodes and nodes with no visible edges
        const updatedNodes = allNodes.map(node => {
            const isExcluded = matchingIds.has(node.id);
            const hasNoEdges = !nodesWithVisibleEdges.has(node.id);
            return { ...node, hidden: isExcluded || hasNoEdges };
        });
        
        network.body.data.nodes.update(updatedNodes);
        network.body.data.edges.update(updatedEdges);
        network.selectNodes([]);
        
        const visibleCount = allNodes.filter(node => 
            !matchingIds.has(node.id) && nodesWithVisibleEdges.has(node.id)
        ).length;
        
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

    function updateEdgeVisibility(network, selectedNodes, isEdgeHiddenByTypeFilter, highlightNodes) {
        const edges = network.body.data.edges.get();
        const nodes = network.body.data.nodes.get();
        const connectedNodes = new Set();
        
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
                return { ...node, hidden: !isConnected };
            });
            network.body.data.nodes.update(updatedNodes);
        }
        
        return connectedNodes;
    }

    return {
        getSelectedEdgeDirection,
        getSelectedFilterMode,
        shouldIncludeEdge,
        buildNeighborhoodFromEdges,
        applyExcludeMode,
        applyIncludeMode,
        updateEdgeVisibility
    };
})();
