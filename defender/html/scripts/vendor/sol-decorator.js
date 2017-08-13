angular.module('solDecorator', ['ngMaterial', 'ngAnimate', 'ngRoute', 'ngSanitize']);

angular.module('solDecorator').directive('solLongClick', function($timeout) {
    return {
        restrict: 'A',
        link: function($scope, $elem, $attrs) {
            $elem.bind('mousedown', function(event) {
                $scope.longClick = true;

                $timeout(function() {
                    if ($scope.longClick) {
                        $scope.$apply(function() {
                            $scope.$eval($attrs.solLongClick)
                        });
                    }
                }, 500);
            });

            $elem.bind('mouseup', function(event) {
                $scope.longClick = false;
            });
        }
    };
});

angular.module('solDecorator').directive('solLongPress', function($timeout) {
    return {
        restrict: 'A',
        link: function($scope, $elem, $attrs) {
            $elem.bind('touchstart', function(event) {
                $scope.longPress = true;

                $timeout(function() {
                    if ($scope.longPress) {
                        $scope.$apply(function() {
                            $scope.$eval($attrs.solLongPress)
                        });
                    }
                }, 500);
            });

            $elem.bind('touchend', function(event) {
                $scope.longPress = false;
            });
        }
    };
});

angular.module('solDecorator').directive('solOnready', function($parse) {
    return {
        restrict: 'A',
        link: function(scope, elem, attrs) {
            elem.ready(function() {
                scope.$apply(function() {
                    var func = $parse(attrs.solOnready);
                func(scope);
            });
        });
       }
   };
});

angular.module('solDecorator').directive("solScaleImage", [
    function() {
        return {
            link: function(scope, elm, attrs) {
                attrs.$observe('solScaleImage', function (value) {
                    elm.css('width', value + 'px');
                    elm.css('height', value + 'px');
                });
            }
        };
    }
]);

angular.module('solDecorator').directive("solBackgroudSrc", [
    function() {
        return {
            link: function(scope, element, attrs) {
                attrs.$observe('solBackgroudSrc', function (value) {
                    element.css('background', 'url(' + value +') center / cover');
                });
            }
        };
    }
]);

angular.module('solDecorator').directive('solSlideable', function () {
    return {
        restrict:'C',
        /*transclude: true,
        templateUrl: function(elem, attr) {
            return '<div class="slideable-content" style="padding-bottom: 5px !important"><div ng-transclude></div></div>';
        },*/
        compile: function (element, attr) {
            var contents = element.html();
            element.html('<div class="sol-slideable-content" style="padding-bottom: 5px !important">' + contents + '</div>');

            return function postLink(scope, element, attrs) {
                // Set default attributes
                attrs.expanded = (attrs.expanded == "true") ? true : false;
                attrs.duration = (!attrs.duration) ? '0.5s' : attrs.duration;
                attrs.easing = (!attrs.easing) ? 'ease' : attrs.easing;

                // Check if starting expanded
                if (!attrs.expanded) {
                    element.css({
                        'height': '0px'
                    });
                }

                // Apply size animation to parent so surrounding views move with child
                element.css({
                    'overflow': 'hidden',
                    'transitionProperty': 'height',
                    'transitionDuration': attrs.duration,
                    'transitionTimingFunction': attrs.easing
                });

                // Apply transform animation to new child to simulate sliding
                var content = element[0].querySelector('.sol-slideable-content');
                var contentStyle = content.style;
                content.setAttribute("expanded", attrs.expanded);
                contentStyle.transitionProperty = 'transform';
                contentStyle.transitionDuration = attrs.duration;
                contentStyle.transitionTimingFunction = attrs.easing;
            };
        }
    };
});

angular.module('solDecorator').directive('solSlideableToggle', function() {
    return {
        restrict: 'A',
        scope: false,
        link: function(scope, element, attrs) {
            var target = document.getElementById(attrs.solSlideableToggle);
            var content = target.querySelector('.sol-slideable-content');
            attrs.expanded = (target.getAttribute("expanded") == "true");

            // Watch for inner changes and update parent
            scope.$watch(
                function() { return content.offsetHeight; },
                function(newValue, oldValue) {
                    if (newValue !== oldValue) {
                        if(attrs.expanded) {
                            target.style.height = newValue + 'px';
                            content.style.transform = 'translate3d(0, 0%, 0)';
                        } else {
                            target.style.height = '0px';
                            content.style.transform = 'translate3d(0, -100%, 0)';
                        }
                    }
                },
                true);

            // Bind click method to toggle view
            element.bind('click', function() {
                var height = content.clientHeight;

                if (!target.style.height) {
                    target.style.height = height + 'px';

                    // TODO Why does target.clientHeight have to be touched again to ensure height takes affect on first call?!?!
                    target.clientHeight = target.clientHeight;
                }

                if(!attrs.expanded) {
                    target.style.height = height + 'px';
                    content.style.transform = 'translate3d(0, 0%, 0)';
                } else {
                    target.style.height = '0px';
                    content.style.transform = 'translate3d(0, -100%, 0)';
                }
                attrs.expanded = !attrs.expanded;
            });
        }
    };
});

angular.module('solDecorator').directive("solFlipper", ['$window', function($window) {
    // Inject animation CSS into document
    var cssString =
    '<style>' +
    '.sol-flipper {' +
    '    overflow: hidden;' +
    '}' +
    '.sol-flip-panel {' +
    '    position: absolute;' +
    '    -webkit-backface-visibility: hidden;' +
    '    backface-visibility: hidden;' +
    '    transition: -webkit-transform .5s;' +
    '    transition: transform .5s;' +
    '    -webkit-transform: perspective(1000px) rotateY(0deg);' +
    '    transform: perspective(1000px) rotateY(0deg);' +
    '}' +
    '.sol-flip-left {' +
    '    -webkit-transform:  perspective(1000px) rotateY(-180deg);' +
    '    transform:  perspective(1000px) rotateY(-180deg);' +
    '}' +
    '.sol-flip-right {' +
    '    -webkit-transform:  perspective(1000px) rotateY(180deg);' +
    '    transform:  perspective(1000px) rotateY(180deg);' +
    '}' +
    '</style>';
    document.head.insertAdjacentHTML("beforeend", cssString);

    function setDimensions(element, width, height) {
        element.style.width = width;
        element.style.height = height;
    }

    return {
        restrict : "E",
        controller: function($scope, $element, $attrs) {
            var self = this;

            self.width = 0;
            self.height = 0;

            self.sides = [];
            self.position = 0;

            $scope.getController = function() {
                return self;
            };

            // Watch for initialization after children added
            $scope.$watch(function() { return self.sides.length; }, function(newValue, oldValue) {
                if (oldValue !== newValue) {
                    self.init();
                }
            });

            self.init = function(count) {
                if (!count) {
                    count = self.sides.length;
                }

                if (count >= 3) {
                    //TODO More than 2 sides found, apply special rules
                    /*for (var i = 0; i < self.sides.length; i++) {
                        var element = self.sides[i];

                        setDimensions(element[0], self.width, self.height);

                        element.on("click", showNext);

                        if (i !== self.position) {
                            element.addClass("flipRight");
                        }
                    }*/

                    // Currently: Default to 2 sides
                    var newArray = [self.sides[0], self.sides[0]];
                    self.sides = newArray;
                    self.init();
                    return;
                } else if (count == 2) {
                    // Two sides found, alternate between the 2
                    setDimensions(self.sides[0][0], self.width, self.height);
                    setDimensions(self.sides[1][0], self.width, self.height);

                    self.sides[0].addClass("sol-flip-left");
                    self.sides[0].removeClass("sol-flip-right");

                    self.sides[0].on("click", showNext);
                    self.sides[1].on("click", showPrevious);
                } else if (count == 1) {
                    // 1 side found, do not alternate but apply dimensions
                    setDimensions(self.sides[0][0], self.width, self.height);
                }
            };

            function getNextSide(current) {
                var position = current;
                position++;

                if (position >= self.sides.length) {
                    position = 0;
                }

                return position;
            }

            function getPreviousSide(current) {
                var position = current;
                position--;

                if (position < 0) {
                    position = Math.max(self.sides.length - 1, 0);
                }

                return position;
            }

            function showSide(index) {
                if (self.disabled) {
                    return;
                }

                var next = getNextSide(index);

                for (var i = 0; i < self.sides.length; i ++) {
                    //self.sides[i].removeClass("sol-flip-right");
                    self.sides[i].removeClass("sol-flip-left");
                }
                //self.sides[next].addClass("sol-flip-left");
                self.sides[next].addClass("sol-flip-right");

                self.position = next;
            }

            function showNext(event) {
                if (self.disabled) {
                    return;
                }

                var current = self.position;
                var next = getNextSide(current);

                for (var i = 0; i < self.sides.length; i ++) {
                    self.sides[i].removeClass("sol-flip-right");
                }
                self.sides[next].addClass("sol-flip-left");

                self.position = next;
            }

            function showPrevious(event) {
                if (self.disabled) {
                    return;
                }

                var previous = getPreviousSide(self.position);

                for (var i = 0; i < self.sides.length; i ++) {
                    self.sides[i].removeClass("sol-flip-left");
                }
                self.sides[previous].addClass("sol-flip-right");

                self.position = previous;
            }
        },
        link: function(scope, element, attrs, ctrl) {
            element.addClass("sol-flipper");

            var percent;
            var maxWidth = $window.innerWidth;
            var maxHeight = $window.innerHeight;

            var width = attrs.flipWidth || "200px";
            var height = attrs.flipHeight || "200px";
            var ratio = attrs.ratio || undefined;

            // Update size to percentages if specified
            if (width.endsWith("%")) {
                percent = parseFloat(width) / 100.0;

                width = Math.min(maxWidth, maxWidth * percent);
            } else if (width.endsWith("px")) {
                width = parseFloat(width);
            }
            if (height.endsWith("%")) {
                percent = parseFloat(height) / 100.0;

                height = Math.min(maxHeight, maxHeight * percent);
            } else if (height.endsWith("px")) {
                height = parseFloat(height);
            }

            // Update sizes if ratio specified
            if (ratio !== undefined) {
                var ratioValues = ratio.split('/');
                ratio = parseFloat(ratioValues[0]) / parseFloat(ratioValues[1]);

                var maxW = width;
                var maxH = height;

                if (width < height) {
                    // View is portrait
                    height = width / ratio;

                    // If new size exceeds original, reverse
                    if (height > maxH) {
                        height = maxH;
                        width = height * ratio;
                    }
                } else {
                    // View is landscape
                    width = height * ratio;

                    // If new size exceeds original, reverse
                    if (width > maxW) {
                        width = maxW;
                        height = width / ratio;
                    }
                }
            }

            // Save controller dimensions and update main element
            ctrl.width = width + 'px';
            ctrl.height = height + 'px';
            setDimensions(element[0], width + 'px', height + 'px');
        }
    };
}]);

angular.module('solDecorator').directive("solFlipPanel", function() {
    return {
        restrict : "E",
        require : "^solFlipper",
        link: function(scope, element, attrs, flipperCtrl) {
            element.addClass("sol-flip-panel");
            flipperCtrl.sides.unshift(element);
        }
    };
});
