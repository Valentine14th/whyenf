/**
 * Node utilities and operations
 */

const GraphNodes = (function() {
    function getNodeName(nodeId) {
        return nodeId.startsWith('LET_') ? nodeId.substring(4) : nodeId;
    }

    function findMatchingNodeIds(network, nodeNames) {
        const allNodes = network.body.data.nodes.get();
        const matchingIds = new Set();
        
        nodeNames.forEach(nodeName => {
            const matches = allNodes.filter(node => 
                node.label === nodeName || 
                node.id === nodeName || 
                node.id === 'LET_' + nodeName
            );
            matches.forEach(m => matchingIds.add(m.id));
        });
        
        return matchingIds;
    }

    function getVisibleNodesFromEdges(network, isEdgeHiddenByTypeFilter) {
        const edges = network.body.data.edges.get();
        const connectedNodes = new Set();
        
        edges.forEach(edge => {
            if (!isEdgeHiddenByTypeFilter(edge)) {
                connectedNodes.add(edge.from);
                connectedNodes.add(edge.to);
            }
        });
        
        return connectedNodes;
    }

    return {
        getNodeName,
        findMatchingNodeIds,
        getVisibleNodesFromEdges
    };
})();
