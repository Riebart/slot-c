myApp.controller('chatMessageCtrl', ['$scope', '$rootScope', '$resource', '$timeout', function ($scope, $rootScope, $resource, $timeout) {

    // Hold the number of seconds until the file upload token expires.
    $scope.file_upload = 0;
    $scope.file_upload_token = null;
    $scope.fileUpload = function () {
        alert('1');
    };

    $rootScope.$on("chatting", function () {
        document.getElementById('chat-message-input').placeholder = "Enter a message and save humanity";
    });
    $rootScope.$on("not chatting", function () {
        document.getElementById('chat-message-input').value = null;
        document.getElementById('chat-message-input').placeholder = "Save your brains, enter your user name";
    });

    $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + DEFAULT_CHANNEL_NAME);
    $scope.MessagesResource = $resource(API_ENDPOINT + "/message");
    $scope.lastTalking = new Date;

    $rootScope.$on('channelChanged', function (event, new_channel) {
        $scope.TalkersResource = $resource(API_ENDPOINT + "/participant" + "?Channel=" + new_channel);
    });

    $scope.FileCountdown = function () {
        var poll = function () {
            $timeout(function () {
                if ($scope.file_upload > 0) {
                    $scope.file_upload -= 1;
                    poll();
                }
            }, 1000);
        };
        poll();
    }

    $scope.chatMessageKeyPressed = function (keyEvent) {
        if ((keyEvent.which === 13) && (!$scope.posting)) {
            $scope.posting = true;
            var message_text = $scope.chatMessage;
            $scope.chatMessage = null;
            console.log('Sending Message: ' + $scope.chatMessage);

            // If this is the /file command
            if (message_text.substring(0, 5) == '/file') {
            }

            var message = {
                // encodeURIComponent() doesn't encode single quotes, which are a problem
                // for API Gateway.
                channel: $rootScope.channel,
                participant: $rootScope.userName,
                message: message_text
            };
            console.log(message);

            $scope.MessagesResource.save(message, function (response) {
                $scope.chatMessage = null;
                $scope.posting = false;
                document.getElementById("chat-message-input").focus();

                // This needs to be more specific.
                if ((response.fields !== undefined) &&
                    (response.fields.AWSAccessKeyId !== undefined)) {
                    $scope.file_upload = response.lifetime;
                    $scope.file_upload_token = response;
                    $scope.FileCountdown();
                }

                $rootScope.$emit('serverMessage', response.server_messages);
                $rootScope.$emit('eventMessageRefresh');
            });
        } else {
            var diff = Date.now() - $scope.lastTalking;
            console.log(diff);

            // send talking update at a maximum rate
            if (diff < 1000) {
                return;
            }

            var message = {
                channel: $rootScope.channel,
                participant: $rootScope.userName
            };

            console.log('Posting to talkers.');
            $scope.TalkersResource.save(message, function () {
                $scope.lastTalking = new Date;
            });
        }
    };

}]);
