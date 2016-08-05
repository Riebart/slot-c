myApp.controller('chatPanelCtrl', ['$scope', '$rootScope', '$resource', '$timeout', function ($scope, $rootScope, $resource, $timeout) {

    $rootScope.backoff_factor = 1.0;
    $scope.adjust_backoff = function () {
        // If it's been more than 60 seconds since the last message, start to increase
        // the backoff factor, up to a maximum value gradually, over the course of
        // 5 minutes (300s), starting 5 minutes after the last message.
        //
        var ms_delta = $scope.default_message_history;
        if ($scope.messages[$scope.channel].length > 0) {
            ms_delta = (new Date).valueOf() - $scope.messages[$scope.channel][0].timestamp;
        }
        // Don't let it go below 1.0, or above 10.0
        return Math.max(1.0, Math.min(1.0 + 9.0 * ((ms_delta - 300000) / 300000), 25.0));
    };

    $scope.init = function () {
        $scope.channel = DEFAULT_CHANNEL_NAME;

        $scope.default_message_history = 3600 * 1000 * 24;
        $scope.lastMessageTime = (new Date).valueOf() - $scope.default_message_history;
        $scope.firstMessageTime = (new Date).valueOf();
        $scope.more_history = {};
        $scope.more_history[$scope.channel] = true;

        $scope.MessagesResource = $resource(API_ENDPOINT + "/message/:channel/:from");
        $scope.messages = {};
        $scope.messages[$scope.channel] = [];
    };

    $scope.init();

    $scope.GetMoreHistory = function () {
        console.log('Retrieving history from Server');
        var Messages = $scope.MessagesResource;
        Messages.get({
            channel: $scope.channel,
            from: -($scope.firstMessageTime - 1)
        }, function (messages) {
            if ($rootScope.chatting) {
                if (!messages.truncated) {
                    $scope.more_history[$scope.channel] = false;
                }
                if (messages.messages.length > 0) {
                    $scope.firstMessageTime = messages.messages[messages.messages.length - 1].timestamp;
                    $scope.messages[$scope.channel] = $scope.messages[$scope.channel].concat(messages.messages);
                }
            }
            else {
                //just in case, for cleanup
                $scope.messages[$scope.channel] = [];
            }
        });
    }

    $scope.PopulateMessages = function (Messages) {
        if ($rootScope.chatting) {
            console.log('Retrieving Messages from Server');
            var t = (new Date).valueOf();
            Messages.get({
                channel: $scope.channel,
                from: $scope.lastMessageTime + 1
            }, function (messages) {
                if ($rootScope.chatting) {
                    if (messages.messages.length > 0) {
                        // If there are no messages for the channel currently, update the first message time.
                        if ($scope.messages[$scope.channel].length == 0) {
                            $scope.firstMessageTime = messages.messages[messages.messages.length - 1].timestamp;
                        }
                        $scope.messages[$scope.channel] = messages.messages.concat($scope.messages[$scope.channel]);
                        $scope.lastMessageTime = $scope.messages[$scope.channel][0].timestamp;
                        $rootScope.backoff_factor = 1.0;
                    }
                        // If there were no new messages, adjust the backoff
                    else if ($scope.messages[$scope.channel].length > 0) {
                        $rootScope.backoff_factor = $scope.adjust_backoff();
                    }
                }
                else {
                    //just in case, for cleanup
                    $scope.messages[$scope.channel] = [];
                }
            });
            return true;
        }
        else {
            return false;
        }
    }

    $rootScope.$on('serverMessage', function (event, server_messages) {
        var ts = new Date;
        var smsgs = []
        for (i in server_messages) {
            smsg = server_messages[i];
            var msg = {
                message: smsg,
                timestamp: ts,
                participant: 'Server',
                source: 'server'
            };
            smsgs.push(msg);
        }
        $scope.messages[$scope.channel] = smsgs.concat($scope.messages[$scope.channel]);
    });

    $rootScope.$on('channelChanged', function (event, new_channel) {
        $scope.channel = new_channel;
        //$scope.MessagesResource = $resource(API_ENDPOINT + "/message" + "?Channel=" + new_channel);
        // If this is a new channel we've never visited, prime the pump
        if ($scope.messages[$scope.channel] == undefined) {
            $scope.messages[$scope.channel] = [];
            $scope.more_history[$scope.channel] = true;
            $scope.lastMessageTime = (new Date).valueOf() - $scope.default_message_history;
            $scope.firstMessageTime = (new Date).valueOf();
            $rootScope.backoff_factor = $scope.adjust_backoff();
        }
        else {
            // If we have messages for this channel, set the first and last timestamps accordingly.
            if ($scope.messages[$scope.channel].length > 0) {
                $scope.lastMessageTime = $scope.messages[$scope.channel][0].timestamp;
                $scope.firstMessageTime = $scope.messages[$scope.channel][$scope.messages[$scope.channel].length - 1].timestamp;
            }
                // If we have no messages for this channel, set the first and last timestamps to defaults.
            else {
                $scope.lastMessageTime = (new Date).valueOf() - $scope.default_message_history;
                $scope.firstMessageTime = (new Date).valueOf();
            }
        }
        // Fetch any messages we missed.
        $scope.PopulateMessages($scope.MessagesResource)
    });

    $scope.MessagesRefresh = function () {
        $scope.PopulateMessages($scope.MessagesResource);
        var poll = function () {
            $timeout(function () {
                if ($scope.PopulateMessages($scope.MessagesResource)) {
                    poll();
                }
            }, 1000 * $rootScope.backoff_factor);
        };
        poll();
    };

    $rootScope.$on('eventMessageRefresh', function () {
        $scope.PopulateMessages($scope.MessagesResource)
    });

    $rootScope.$on("chatting", function () {
        $scope.init();
        $scope.MessagesRefresh();
    });

    $rootScope.$on("not chatting", function () {
        //clear our model, which will clear out the messages from the panel
        $scope.messages = {};
    });

    $scope.$on('async_init', $scope.MessagesRefresh);

    if (localStorage.getItem('userName') !== null) {
        $scope.$emit('async_init');
    }

}]);
