/**
 * Rankings widget functionality
 */

const GraphRankings = (function() {
    function getNodeName(nodeId) {
        return nodeId.startsWith('LET_') ? nodeId.substring(4) : nodeId;
    }

    function updateRankings(network, selectedNodes, checkboxes, isEdgeHiddenByTypeFilter) {
        const outgoingRanking = document.getElementById('outgoing-ranking');
        const inboundRanking = document.getElementById('inbound-ranking');
        
        if (!outgoingRanking || !inboundRanking) return;
        
        const visibleNodes = network.body.data.nodes.get().filter(node => !node.hidden);
        const visibleEdges = network.body.data.edges.get().filter(edge => !edge.hidden && !isEdgeHiddenByTypeFilter(edge));
        
        // Count edges for each node
        const outgoingCounts = {};
        const inboundCounts = {};
        
        visibleNodes.forEach(node => {
            outgoingCounts[node.id] = 0;
            inboundCounts[node.id] = 0;
        });
        
        visibleEdges.forEach(edge => {
            if (outgoingCounts.hasOwnProperty(edge.from)) outgoingCounts[edge.from]++;
            if (inboundCounts.hasOwnProperty(edge.to)) inboundCounts[edge.to]++;
        });
        
        // Sort and slice top 15
        const sortedByOutgoing = visibleNodes
            .map(node => ({ id: node.id, label: node.label, count: outgoingCounts[node.id] }))
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count)
            .slice(0, 15);
        
        const sortedByInbound = visibleNodes
            .map(node => ({ id: node.id, label: node.label, count: inboundCounts[node.id] }))
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count)
            .slice(0, 15);
        
        // Render rankings
        renderRanking(outgoingRanking, sortedByOutgoing, selectedNodes, checkboxes);
        renderRanking(inboundRanking, sortedByInbound, selectedNodes, checkboxes);
    }

    function renderRanking(container, items, selectedNodes, checkboxes) {
        container.innerHTML = '';
        
        if (items.length === 0) {
            container.innerHTML = '<div style="color: #95a5a6; font-size: 11px; padding: 5px;">No edges</div>';
            return;
        }
        
        items.forEach((item, index) => {
            const rankItem = document.createElement('div');
            rankItem.className = 'ranking-item';
            
            const nodeName = getNodeName(item.id);
            if (selectedNodes.has(item.label) || selectedNodes.has(nodeName)) {
                rankItem.classList.add('selected');
            }
            
            rankItem.innerHTML = `
                <span class="node-name" title="${item.label}">${index + 1}. ${item.label}</span>
                <span class="edge-count">${item.count}</span>
            `;
            
            rankItem.addEventListener('click', function() {
                const checkbox = Array.from(checkboxes).find(cb => cb.value === nodeName);
                if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
            
            container.appendChild(rankItem);
        });
    }

    function setupRankingsToggle(rankingsToggleBtn, rankingsContent, rankingsHeader) {
        if (rankingsToggleBtn && rankingsContent && rankingsHeader) {
            rankingsToggleBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (rankingsContent.classList.contains('collapsed')) {
                    rankingsContent.classList.remove('collapsed');
                    rankingsToggleBtn.textContent = 'Hide';
                } else {
                    rankingsContent.classList.add('collapsed');
                    rankingsToggleBtn.textContent = 'Show';
                }
            });
            
            rankingsHeader.addEventListener('click', function(e) {
                if (e.target !== rankingsToggleBtn) {
                    rankingsToggleBtn.click();
                }
            });
        }
    }

    return {
        updateRankings,
        setupRankingsToggle
    };
})();
