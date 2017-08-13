var Solari = (function(parent) {
    // Sub Modules
    var ui = parent.ui = parent.ui || {};

    // Private functions
    function onSelectFiles(event, callback) {
        onDragHover(event);

        if (typeof callback !== "function") {
            return;
        }

        callback(event.target.files || event.dataTransfer.files);
    }

    function onDragHover(event) {
        event.stopPropagation();
        event.preventDefault();

        // Only update drag region classes
        if (event.target.classList.contains('drag-region')) {
            if (event.type == "dragover") {
                if (!event.target.classList.contains('hover')) {
                    event.target.classList.add('hover');
                }
            } else {
                event.target.classList.remove('hover');
            }
        }
    }

    function hexToRGBA(hex) {
        if (hex === undefined) {
            return undefined;
        }

        hex = hex.replace('#','');

        if (hex.length == 8) {
            a = parseInt(hex.substring(0, 2), 16);
            r = parseInt(hex.substring(2, 4), 16);
            g = parseInt(hex.substring(4, 6), 16);
            b = parseInt(hex.substring(6, 8), 16);
        } else if (hex.length == 4) {
            a = parseInt(hex.substring(0, 1), 16);
            r = parseInt(hex.substring(1, 2), 16);
            g = parseInt(hex.substring(2, 3), 16);
            b = parseInt(hex.substring(3, 4), 16);
        } else {
            return undefined;
        }

        return 'rgba(' + r + ',' + g + ',' + b + ',' + (a / 255) +')';
    }

    function rgbaToHex(r, g, b, a) {
        a = Solari.utils.padZeros(parseInt(a).toString(16), 2);
        r = Solari.utils.padZeros(parseInt(r).toString(16), 2);
        g = Solari.utils.padZeros(parseInt(g).toString(16), 2);
        b = Solari.utils.padZeros(parseInt(b).toString(16), 2);

        return '#' + a + r + g + b;
    }

    function rgbaStringToHex(rgba) {
        if (rgba === undefined) {
            return undefined;
        }

        rgba = rgba.replace('rgba(','');
        rgba = rgba.replace(')','');
        rgba = rgba.replace(' ','');
        rgba = rgba.split(',');

        a = parseInt(parseFloat(rgba[3]) * 255) || 0;
        r = parseInt(rgba[0]) || 0;
        g = parseInt(rgba[1]) || 0;
        b = parseInt(rgba[2]) || 0;

        return rgbaToHex(r, g, b, a);
    }

    function drawText(x, y, text, ctx) {
        ctx.font = '14pt Calibri';
        ctx.textAlign = 'center';
        ctx.lineWidth = 1;

        ctx.shadowColor = "black";
        ctx.shadowBlur = 7;

        ctx.strokeStyle = 'black';
        ctx.strokeText(text, x, y);

        ctx.fillStyle = 'white';
        ctx.fillText(text, x, y);

        ctx.shadowBlur = 0;
    }

    function drawCircle(cx, cy, radius, color, ctx) {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
        ctx.fill();
    }

    function drawOutlineCircle(cx, cy, radius, lineWidth, color, ctx) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, 2 * Math.PI);
        ctx.stroke();
    }

    function drawSquare(x, y, radius, color, ctx) {
        ctx.fillStyle = color;
        ctx.fillRect(x, y, radius, radius);
    }

    function drawOutlineSquare(x, y, radius, lineWidth, color, ctx) {
        ctx.strokeStyle = color;
        ctx.lineWidth = lineWidth;
        ctx.strokeRect(x, y, radius, radius);
    }

    function containedInCircle(x, y, cx, cy, radius) {
        return (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius * radius;
    }

    function containedInSquare(mx, my, x, y, size) {
        return  (x <= mx) && (y <= my) && (x + size >= mx) && (y + size >= my);
    }

    function Coordinate(x, y, z, size, color, shape, id) {
        this.x = x || 0;
        this.y = y || 0;
        this.z = z || 0;
        this.size = size || 20;
        this.color = color || hexToRGBA('#AAAAAAAA');
        this.shape = shape || 0;
        this.id = id || undefined;
    }

    Coordinate.prototype.draw = function(ctx, ratio) {
        if (!ratio) {
            ratio = 1;
        }

        // Draw shape
        if (this.shape === 0) {
            drawCircle(
                this.x * ratio,
                this.y * ratio,
                this.size * ratio,
                this.color,
                ctx
            );
        } else {
            drawSquare(
                (this.x - this.size) * ratio,
                (this.y - this.size) * ratio,
                (this.size * 2) * ratio,
                 this.color,
                 ctx
             );
        }

        // Draw position identifier
        if (this.id !== undefined) {
            drawText(this.x * ratio, (this.y * ratio) + 5, this.id + 1, ctx);
        }
    };

    Coordinate.prototype.contains = function(mx, my) {
        if (this.shape === 0) {
            return containedInCircle(mx, my, this.x, this.y, this.size);
        } else {
            return containedInSquare(mx, my, this.x - this.size, this.y - this.size, this.size * 2);
        }
    };

    function CoordinateCanvas(canvas) {
        var self = this;

        self.canvas = canvas;
        self.ctx = canvas.getContext('2d');
        self.canvasUpdateTimer = null;
        self.canvasUpdateInterval = 1000 / 60;

        self.width = 0;
        self.height = 0;
        self.drawRatio = 1;

        self.valid = false;
        self.coords = [];
        self.dragging = false;
        self.selection = undefined;
        self.dragoffx = 0;
        self.dragoffy = 0;

        self.viewOffsetX = 0;
        self.viewOffsetY = 0;

        self.drawCallBack = undefined;
        self.onDoubleClickListener = undefined;
        self.onSelectListener = undefined;

        self.highlightColor = '#CC0000';
        self.highlightWidth = 2;

        self.lockTouch = false;

        canvas.addEventListener('selectstart', function(event) {
            // Prevent text highlighting
            event.preventDefault();
            return false;
        }, false);

        canvas.addEventListener('mousedown', function(event) {
            if (self.lockTouch) {
                return;
            }

            self.startUpdates();

            // Check if user selected a coordinate
            var pos = self.getMousePos(event);
            self.selection = undefined;

            var selected;
            for (var i = self.coords.length - 1; i >= 0; i--) {
                if (self.coords[i].contains(pos.x / self.drawRatio, pos.y / self.drawRatio)) {
                    self.selection = self.coords[i];

                    self.dragoffx = pos.x / self.drawRatio - self.selection.x;
                    self.dragoffy = pos.y / self.drawRatio - self.selection.y;
                    self.dragging = true;

                    selected = self.selection.id;
                }
            }

            if (self.onSelectListener) {
                self.onSelectListener(selected);
            }

            self.invalidate();
        }, true);

        canvas.addEventListener('mousemove', function(event) {
            if (self.lockTouch) {
                return;
            }

            if (self.dragging) {
                var pos = self.getMousePos(event);
                var ratio = self.drawRatio;

                self.selection.x = Math.round((pos.x / ratio) - self.dragoffx);
                self.selection.y = Math.round((pos.y / ratio) - self.dragoffy);
                self.valid = false;
            }
        }, true);

        canvas.addEventListener('mouseup', function(event) {
            if (self.lockTouch) {
                return;
            }

            self.dragging = false;
            self.stopUpdates();
        }, true);

        canvas.addEventListener('dblclick', function(event) {
            if (self.lockTouch) {
                return;
            }

            if (self.onDoubleClickListener !== null) {
                self.onDoubleClickListener(event);
            }
        }, true);

        // Perform at least one initialization pass
        self.init();
    }

    CoordinateCanvas.prototype.init = function() {
        var self = this;
        var canvas = self.canvas;

        this.setDimensions(canvas.width, canvas.height);

        // Account for border or padding
        if (document.defaultView && document.defaultView.getComputedStyle) {
            self.viewOffsetX += parseInt(document.defaultView.getComputedStyle(canvas, null).paddingLeft) || 0;
            self.viewOffsetX += parseInt(document.defaultView.getComputedStyle(canvas, null).borderLeftWidth) || 0;

            self.viewOffsetY += parseInt(document.defaultView.getComputedStyle(canvas, null).paddingTop) || 0;
            self.viewOffsetY += parseInt(document.defaultView.getComputedStyle(canvas, null).borderTopWidth) || 0;
        }

        // Account for fixed position bars
        var html = document.body.parentNode;
        self.viewOffsetX += parseInt(html.offsetLeft) || 0;
        self.viewOffsetY += parseInt(html.offsetTop) || 0;

        self.stopUpdates();
    };

    CoordinateCanvas.prototype.lock = function () {
        this.lockTouch = true;
    };

    CoordinateCanvas.prototype.unlock = function () {
        this.lockTouch = false;
    };

    CoordinateCanvas.prototype.setDimensions = function(width, height) {
        this.width = width;
        this.height = height;
        this.canvas.width = width;
        this.canvas.height = height;
    };

    CoordinateCanvas.prototype.setDrawCallback = function(callback) {
        this.drawCallBack = callback;
    };

    CoordinateCanvas.prototype.setOnDoubleClickListener = function(callback) {
        this.onDoubleClickListener = callback;
    };

    CoordinateCanvas.prototype.setOnSelectListener = function(callback) {
        this.onSelectListener = callback;
    };

    CoordinateCanvas.prototype.startUpdates = function() {
        var self = this;

        if (self.canvasUpdateTimer === null) {
            self.valid = false;
            self.canvasUpdateTimer = setInterval(function() {
                self.draw();
            }, self.canvasUpdateInterval);
        }
    };

    CoordinateCanvas.prototype.stopUpdates = function() {
        var self = this;

        if (self.canvasUpdateTimer !== null) {
            // Delay 100ms to account for potential pending draw
            setTimeout(function() {
                clearInterval(self.canvasUpdateTimer);
                self.canvasUpdateTimer = null;
            }, 100);
        }
    };

    CoordinateCanvas.prototype.selectCoordinate = function(index, ignoreId) {
        var selected;
        if (ignoreId === true) {
            if (index > -1 && index < this.coords.length) {
                this.selection = this.coords[index];
                selected = index;
            } else {
                this.selection = undefined;
            }
        } else {
            for (var i = 0; i < this.coords.length; i++) {
                var coord = this.coords[i];
                if (coord.id === index) {
                    this.selection = coord;
                    selected = coord.id;
                    break;
                }
            }

            if (selected === undefined) {
                this.selection = undefined;
            }
        }

        if (this.onSelectListener) {
            this.onSelectListener(selected);
        }

        this.invalidate();
    };

    CoordinateCanvas.prototype.addCoordinate = function(coordinate, position, strictPositioning) {
        if (position) {
            var maxCoord = this.coords.length;
            position = position < 0 ? 0 : position;

            if (strictPositioning) {
                position = position > maxCoord ? maxCoord : position;

                for (var i = position; i < maxCoord; i++) {
                    this.coords[i].id = i + 1;
                }
            }
        } else {
            position = this.coords.length;
        }
        coordinate.id = (strictPositioning || coordinate.id === undefined) ? position : coordinate.id;
        this.coords.splice(position, 0, coordinate);
        this.invalidate();
    };

    CoordinateCanvas.prototype.removeCoordinate = function(index, ignoreId, ignoreDeselect) {
        var selected;
        if (ignoreId === true) {
            if (index > -1 && index < this.coords.length) {
                selected = index;
                this.coords.splice(index, 1);
            }
        } else {
            for (var i = 0; i < this.coords.length; i++) {
                var id = this.coords[i].id;
                if (id === index) {
                    selected = id;
                    this.coords.splice(i, 1);
                    break;
                }
            }
        }

        if (selected !== undefined) {
            // Coordinate was removed, unselect
            this.selection = undefined;

            if (ignoreDeselect !== true) {
                this.selectCoordinate(undefined);
            }
        }

        this.invalidate();
    };

    CoordinateCanvas.prototype.reset = function() {
        this.selectCoordinate(undefined);
        this.coords.length = 0;
        this.invalidate();
    };

    CoordinateCanvas.prototype.getMousePos = function(event) {
        var canvas = this.canvas;
        var offsetX = 0;
        var offsetY = 0;

        if (canvas.offsetParent !== undefined) {
            while ((canvas = canvas.offsetParent)) {
                offsetX += canvas.offsetLeft;
                offsetY += canvas.offsetTop;
            }
        }

        offsetX += this.viewOffsetX;
        offsetY += this.viewOffsetY;

        return {x: event.pageX - offsetX, y: event.pageY - offsetY};
    };

    CoordinateCanvas.prototype.invalidate = function() {
        this.valid = false;
        this.draw();
    };

    CoordinateCanvas.prototype.clear = function() {
        this.ctx.clearRect(0, 0, this.width, this.height);
    };

    CoordinateCanvas.prototype.draw = function() {
        if (!this.valid) {
            var ctx = this.ctx;
            var coords = this.coords;
            var sel = this.selection;
            var ratio = this.drawRatio;

            // Draw coordinates except user selection
            this.clear();
            for (var i = 0; i < coords.length; i++) {
                var coord = coords[i];
                // TODO skip out of bounds coordinates
                if (sel !== undefined && sel == coord) {
                    continue;
                } else {
                    coord.draw(ctx, ratio);
                }
            }

            // Draw user selection last to always bring to front with outline
            if (sel !== undefined) {
                sel.draw(ctx, ratio);

                ctx.strokeStyle = this.highlightColor;
                ctx.lineWidth = this.highlightWidth;

                if (sel.shape === 0) {
                    drawOutlineCircle(sel.x * ratio, sel.y * ratio, sel.size * ratio, 2, this.highlightColor, ctx);
                } else {
                    drawOutlineSquare((sel.x - sel.size) * ratio, (sel.y - sel.size) * ratio, (sel.size * 2) * ratio, this.highlightWidth, this.highlightColor, ctx);
                }
            }

            this.valid = true;

            if (this.drawCallBack) {
                this.drawCallBack();
            }
        }
    };

    // Public functions
    ui.onSelectFiles = onSelectFiles;
    ui.onDragHover = onDragHover;
    ui.Coordinate = Coordinate;
    ui.CoordinateCanvas = CoordinateCanvas;
    ui.hexToRGBA = hexToRGBA;
    ui.rgbaToHex = rgbaToHex;
    ui.rgbaStringToHex = rgbaStringToHex;

    return parent;
}(Solari || {}));
