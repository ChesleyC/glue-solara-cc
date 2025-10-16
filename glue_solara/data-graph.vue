<template>
  <div class="data-graph-container" :style="containerStyle">
    <canvas
      ref="canvas"
      :width="width"
      :height="height"
      @mousemove="onMouseMove"
      @click="onClick"
      @mouseleave="onMouseLeave"
      style="cursor: pointer; border: 1px solid #ccc; border-radius: 4px;"
    />
  </div>
</template>

<script>
// Data Graph Visualization Component
// Based on Qt's DataGraphWidget (glue-qt/dialogs/link_editor/data_graph.py)
// Implements circular node layout with interactive selection

export default {
  name: 'DataGraphCanvas',
  props: {
    nodes: {
      type: Array,
      default: () => []
    },
    edges: {
      type: Array,
      default: () => []
    },
    width: {
      type: Number,
      default: 800
    },
    height: {
      type: Number,
      default: 300
    },
    selectedIndex1: {
      type: Number,
      default: null
    },
    selectedIndex2: {
      type: Number,
      default: null
    }
  },
  data() {
    return {
      ctx: null,
      nodePositions: [],
      labelPositions: [],
      selectionLevel: 0,
      selectedNode1Index: null,
      selectedNode2Index: null,
      hoveredNodeIndex: null,
      hoveredEdgeKey: null,
      COLOR_SELECTED: 'rgb(51, 230, 51)',
      COLOR_CONNECTED: 'rgb(153, 230, 230)',
      COLOR_DISCONNECTED: 'rgb(230, 153, 153)',
      COLOR_DEFAULT_NODE: 'rgb(204, 204, 204)',
      COLOR_DEFAULT_EDGE: 'rgb(128, 128, 128)',
      RADIUS: 15
    }
  },
  computed: {
    containerStyle() {
      return {
        width: `${this.width}px`,
        height: `${this.height}px`,
        position: 'relative'
      }
    }
  },
  watch: {
    nodes: {
      handler() {
        this.layout()
        this.syncExternalSelection()
        this.render()
      },
      deep: true
    },
    edges: {
      handler() {
        this.render()
      },
      deep: true
    },
    selectedIndex1() {
      this.syncExternalSelection()
    },
    selectedIndex2() {
      this.syncExternalSelection()
    }
  },
  mounted() {
    this.ctx = this.$refs.canvas.getContext('2d')
    this.ctx.font = '10pt Arial'
    this.layout()
    this.syncExternalSelection()
    this.render()
  },
  methods: {
    isValidIndex(index) {
      return Number.isInteger(index) && index >= 0 && index < this.nodes.length
    },
    layout() {
      this.nodePositions = []
      this.labelPositions = []

      if (!this.nodes.length) {
        return
      }

      const centerX = this.width / 2
      const centerY = this.height / 2
      const radius = this.height / 3
      this.RADIUS = this.height / 30

      this.nodes.forEach((node, i) => {
        const angle = (2 * Math.PI * i) / this.nodes.length
        const nx = radius * Math.cos(angle) + centerX
        const ny = radius * Math.sin(angle) + centerY
        this.nodePositions.push({ x: nx, y: ny, index: node.index })
      })

      const leftNodes = this.nodePositions.filter(p => p.x < centerX)
      const rightNodes = this.nodePositions.filter(p => p.x >= centerX)

      leftNodes.sort((a, b) => b.y - a.y)
      rightNodes.sort((a, b) => b.y - a.y)

      leftNodes.forEach((nodePos, i) => {
        const y = this.height - ((i + 1) / (leftNodes.length + 1)) * this.height
        this.labelPositions.push({
          x: centerX - radius,
          y,
          index: nodePos.index,
          align: 'right'
        })
      })

      rightNodes.forEach((nodePos, i) => {
        const y = this.height - ((i + 1) / (rightNodes.length + 1)) * this.height
        this.labelPositions.push({
          x: centerX + radius,
          y,
          index: nodePos.index,
          align: 'left'
        })
      })
    },
    render() {
      if (!this.ctx) {
        return
      }

      this.ctx.clearRect(0, 0, this.width, this.height)

      const colors = this.calculateColors()

      this.drawEdges(colors)
      this.drawLabelLines()
      this.drawLabels()
      this.drawNodes(colors)
    },
    drawEdges(colors) {
      this.edges.forEach(edge => {
        const pos1 = this.getNodePosition(edge.source)
        const pos2 = this.getNodePosition(edge.target)

        if (!pos1 || !pos2) {
          return
        }

        this.ctx.beginPath()
        this.ctx.moveTo(pos1.x, pos1.y)
        this.ctx.lineTo(pos2.x, pos2.y)

        if (edge.link_type === 'join') {
          this.ctx.setLineDash([5, 5])
        } else {
          this.ctx.setLineDash([])
        }

        const edgeKey = this.edgeKey(edge.source, edge.target)
        this.ctx.lineWidth = colors.edges[edgeKey] ? 3 : 2
        this.ctx.strokeStyle = colors.edges[edgeKey] || this.COLOR_DEFAULT_EDGE
        this.ctx.stroke()
      })

      this.ctx.setLineDash([])
    },
    drawLabelLines() {
      this.labelPositions.forEach(labelPos => {
        const nodePos = this.getNodePosition(labelPos.index)
        if (!nodePos) {
          return
        }

        const midX = (labelPos.x + nodePos.x) / 2

        this.ctx.beginPath()
        this.ctx.moveTo(labelPos.x, labelPos.y)
        this.ctx.lineTo(midX, labelPos.y)
        this.ctx.lineTo(nodePos.x, nodePos.y)
        this.ctx.strokeStyle = this.COLOR_DEFAULT_EDGE
        this.ctx.lineWidth = 1
        this.ctx.stroke()
      })
    },
    drawLabels() {
      this.labelPositions.forEach(labelPos => {
        const label = this.getNodeLabel(labelPos.index)

        this.ctx.fillStyle = '#000'
        this.ctx.textBaseline = 'middle'
        this.ctx.textAlign = labelPos.align === 'right' ? 'right' : 'left'
        this.ctx.fillText(label, labelPos.x, labelPos.y)
      })
    },
    drawNodes(colors) {
      this.nodePositions.forEach(pos => {
        this.ctx.beginPath()
        this.ctx.arc(pos.x, pos.y, this.RADIUS, 0, 2 * Math.PI)

        const key = this.nodeKey(pos.index)
        this.ctx.fillStyle = colors.nodes[key] || this.COLOR_DEFAULT_NODE
        this.ctx.fill()

        this.ctx.strokeStyle = '#000'
        this.ctx.lineWidth = 1
        this.ctx.stroke()
      })
    },
    calculateColors() {
      const colors = { nodes: {}, edges: {} }

      if (this.selectionLevel === 0 || this.selectedNode1Index === null) {
        return colors
      }

      if (this.selectionLevel === 1) {
        const reachable = this.findConnections(this.selectedNode1Index)
        const reachableSet = new Set([...reachable.direct, ...reachable.indirect])

        this.nodes.forEach(node => {
          const key = this.nodeKey(node.index)
          if (node.index === this.selectedNode1Index) {
            colors.nodes[key] = this.COLOR_SELECTED
          } else if (reachableSet.has(node.index)) {
            colors.nodes[key] = this.COLOR_CONNECTED
          } else {
            colors.nodes[key] = this.COLOR_DISCONNECTED
          }
        })

        this.edges.forEach(edge => {
          if (edge.source === this.selectedNode1Index || edge.target === this.selectedNode1Index) {
            const edgeKey = this.edgeKey(edge.source, edge.target)
            colors.edges[edgeKey] = this.COLOR_CONNECTED
          }
        })

        return colors
      }

      if (this.selectionLevel >= 2 && this.selectedNode2Index !== null) {
        const edge = this.getEdgeBetween(this.selectedNode1Index, this.selectedNode2Index)

        this.nodes.forEach(node => {
          const key = this.nodeKey(node.index)
          if (node.index === this.selectedNode1Index || node.index === this.selectedNode2Index) {
            colors.nodes[key] = this.COLOR_SELECTED
          }
        })

        if (edge) {
          colors.edges[this.edgeKey(edge.source, edge.target)] = this.COLOR_SELECTED
        }

        return colors
      }

      return colors
    },
    findConnections(index) {
      const direct = []
      const indirect = []
      const visited = new Set([index])
      let frontier = [index]
      let depth = 0

      while (frontier.length) {
        const nextFrontier = []

        frontier.forEach(current => {
          this.edges.forEach(edge => {
            let neighbor = null
            if (edge.source === current) {
              neighbor = edge.target
            } else if (edge.target === current) {
              neighbor = edge.source
            }

            if (neighbor === null || visited.has(neighbor)) {
              return
            }

            visited.add(neighbor)
            if (depth === 0) {
              direct.push(neighbor)
            } else {
              indirect.push(neighbor)
            }

            nextFrontier.push(neighbor)
          })
        })

        frontier = nextFrontier
        depth += 1
      }

      return { direct, indirect }
    },
    onClick(event) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top

      const clickedNode = this.findNodeAt(x, y)
      const clickedEdge = this.findEdgeAt(x, y)

      if (clickedNode !== null) {
        this.handleNodeClick(clickedNode)
      } else if (clickedEdge) {
        this.handleEdgeClick(clickedEdge)
      } else {
        this.clearSelection()
      }

      this.render()
      this.emitSelection()
    },

    clearSelection() {
      this.selectionLevel = 0
      this.selectedNode1Index = null
      this.selectedNode2Index = null
    },
    handleNodeClick(index) {
      if (this.selectionLevel === 0) {
        this.selectedNode1Index = index
        this.selectedNode2Index = null
        this.selectionLevel = 1
      } else if (this.selectionLevel === 1) {
        if (index === this.selectedNode1Index) {
          this.clearSelection()
        } else {
          this.selectedNode2Index = index
          this.selectionLevel = 2
        }
      } else if (this.selectionLevel === 2) {
        if (index === this.selectedNode1Index && this.selectedNode2Index !== null) {
          // Promote second node to keep ordering intuitive
          this.selectedNode1Index = this.selectedNode2Index
          this.selectedNode2Index = null
          this.selectionLevel = 1
        } else if (index === this.selectedNode2Index) {
          this.selectedNode2Index = null
          this.selectionLevel = 1
        } else {
          this.selectedNode1Index = index
          this.selectedNode2Index = null
          this.selectionLevel = 1
        }
      }
    },
    handleEdgeClick(edge) {
      if (
        this.selectionLevel === 1 &&
        this.selectedNode1Index !== null &&
        (edge.source === this.selectedNode1Index || edge.target === this.selectedNode1Index)
      ) {
        const other = edge.source === this.selectedNode1Index ? edge.target : edge.source
        this.selectedNode2Index = other
      } else {
        this.selectedNode1Index = edge.source
        this.selectedNode2Index = edge.target
      }
      this.selectionLevel = 2
    },
    onMouseMove(event) {
      const rect = this.$refs.canvas.getBoundingClientRect()
      const x = event.clientX - rect.left
      const y = event.clientY - rect.top

      const hoveredNode = this.findNodeAt(x, y)
      const hoveredEdge = this.findEdgeAt(x, y)

      if (hoveredNode !== this.hoveredNodeIndex || hoveredEdge !== this.hoveredEdgeKey) {
        this.hoveredNodeIndex = hoveredNode
        this.hoveredEdgeKey = hoveredEdge ? this.edgeKey(hoveredEdge.source, hoveredEdge.target) : null
      }
    },
    onMouseLeave() {
      this.hoveredNodeIndex = null
      this.hoveredEdgeKey = null
    },
    findNodeAt(x, y) {
      for (const pos of this.nodePositions) {
        const dx = x - pos.x
        const dy = y - pos.y
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist <= this.RADIUS) {
          return pos.index
        }
      }
      return null
    },
    findEdgeAt(x, y) {
      for (const edge of this.edges) {
        const pos1 = this.getNodePosition(edge.source)
        const pos2 = this.getNodePosition(edge.target)
        if (!pos1 || !pos2) {
          continue
        }

        const dist = this.distanceToLine(x, y, pos1.x, pos1.y, pos2.x, pos2.y)
        if (dist < 5) {
          return edge
        }
      }
      return null
    },
    distanceToLine(px, py, x1, y1, x2, y2) {
      const A = px - x1
      const B = py - y1
      const C = x2 - x1
      const D = y2 - y1

      const dot = A * C + B * D
      const lenSq = C * C + D * D
      let param = -1

      if (lenSq !== 0) {
        param = dot / lenSq
      }

      let xx
      let yy

      if (param < 0) {
        xx = x1
        yy = y1
      } else if (param > 1) {
        xx = x2
        yy = y2
      } else {
        xx = x1 + param * C
        yy = y1 + param * D
      }

      const dx = px - xx
      const dy = py - yy
      return Math.sqrt(dx * dx + dy * dy)
    },
    getNodePosition(index) {
      return this.nodePositions.find(p => p.index === index)
    },
    getNodeLabel(index) {
      const node = this.nodes.find(n => n.index === index)
      return node ? node.label : `Dataset ${index}`
    },
    nodeKey(index) {
      return `node-${index}`
    },
    edgeKey(source, target) {
      const a = Math.min(source, target)
      const b = Math.max(source, target)
      return `edge-${a}-${b}`
    },
    getEdgeBetween(source, target) {
      if (source === null || target === null) {
        return null
      }
      const key = this.edgeKey(source, target)
      return (
        this.edges.find(edge => this.edgeKey(edge.source, edge.target) === key) || null
      )
    },
    emitSelection() {
      const edge = this.getEdgeBetween(this.selectedNode1Index, this.selectedNode2Index)
      this.$emit('selection-changed', {
        data1Index: this.selectedNode1Index,
        data2Index: this.selectedNode2Index,
        selectionLevel: this.selectionLevel,
        hasEdge: !!edge,
        linkCount: edge && typeof edge.count === 'number' ? edge.count : 0
      })
    },
    syncExternalSelection() {
      const index1 = this.isValidIndex(this.selectedIndex1) ? this.selectedIndex1 : null
      const index2 = this.isValidIndex(this.selectedIndex2) ? this.selectedIndex2 : null

      this.selectedNode1Index = index1
      this.selectedNode2Index = index2

      if (index1 !== null && index2 !== null) {
        this.selectionLevel = 2
      } else if (index1 !== null || index2 !== null) {
        this.selectionLevel = 1
      } else {
        this.selectionLevel = 0
      }

      this.render()
    }
  }
}
</script>

<style scoped>
.data-graph-container {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f8f8f8;
  border-radius: 4px;
  padding: 10px;
}
</style>
